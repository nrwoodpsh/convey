"""Kafka 발행/소비 헬퍼 — confluent-kafka + Avro + Schema Registry (㊱ P2, 실무 정석).

전송 클라이언트를 aiokafka → **confluent-kafka**(librdkafka)로 교체하고, 메시지를 **Avro**로
직렬화해 **Confluent Schema Registry**에 스키마를 등록한다. 봉투(㊱ P1)는 그대로 — Avro 레코드로 표현.

- 발행: EventEnvelope(메타)+payload(JSON 문자열)를 Avro 인코딩 → Registry가 subject(<topic>-value) 관리.
- 소비: Avro 디코딩 → payload(JSON) 복원 → 핸들러엔 도메인 dict만(핸들러 무변경).
- 하위호환: confluent Avro 와이어(매직바이트 0)와 레거시 날 JSON(`{`)을 **이중 경로**로 처리(전환·재생 안전).
- 동기 confluent 호출은 `asyncio.to_thread`로 격리(서비스는 여전히 async 시그니처).

payload는 봉투 Avro의 `string` 필드(JSON) — 봉투 메타는 필드형 Avro라 Registry 호환성 규칙이 적용된다.
(이벤트별 payload 필드형 Avro 스키마는 후속.)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

RETRY_MAX = 3          # 소비 실패 재시도 횟수(초과 시 DLQ) — 계약(api-contract-eventing)
DLQ_SUFFIX = ".dlq"    # DLQ 토픽 접미사(예: research.ingested.dlq)
_RETRY_BACKOFF = 0.5   # 재시도 간 백오프(초, 선형)

from confluent_kafka import Consumer, Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

from common.envelope import make_envelope, unwrap

logger = logging.getLogger(__name__)

# 봉투 Avro 스키마(㊱ P2) — 메타는 필드형(호환성 대상), payload는 JSON 문자열(다형 도메인 데이터).
ENVELOPE_AVRO_SCHEMA = json.dumps(
    {
        "type": "record",
        "name": "EventEnvelope",
        "namespace": "convey.eventing",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "event_type", "type": "string"},
            {"name": "version", "type": "int"},
            {"name": "occurred_at", "type": "string"},
            {"name": "producer", "type": "string"},
            {"name": "payload", "type": "string"},
            {"name": "key", "type": ["null", "string"], "default": None},
        ],
    }
)


def _registry_url() -> str:
    return os.environ.get("SCHEMA_REGISTRY_URL", "http://schema-registry:8081")


class KafkaProducer:
    """confluent-kafka 프로듀서 + Avro 직렬화. producer_name은 봉투 발행자 메타."""

    def __init__(
        self, bootstrap: str, producer_name: str = "unknown", schema_registry_url: str = ""
    ) -> None:
        self._bootstrap = bootstrap
        self._name = producer_name
        self._registry_url = schema_registry_url or _registry_url()
        self._producer: Producer | None = None
        self._serializer: AvroSerializer | None = None

    async def start(self) -> None:
        self._producer = Producer(
            {"bootstrap.servers": self._bootstrap, "enable.idempotence": True}
        )
        registry = SchemaRegistryClient({"url": self._registry_url})
        self._serializer = AvroSerializer(
            registry, ENVELOPE_AVRO_SCHEMA, lambda obj, ctx: obj  # obj는 이미 스키마 형태 dict
        )

    async def stop(self) -> None:
        if self._producer is not None:
            await asyncio.to_thread(self._producer.flush, 10)

    def _publish_sync(self, topic: str, value: bytes, key: str | None) -> None:
        assert self._producer is not None
        self._producer.produce(
            topic, value=value, key=key.encode() if key else None
        )
        self._producer.flush(10)  # 저부하 — 전달 보장 후 반환(send_and_wait 유사)

    async def publish(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        """payload를 봉투로 감싸 Avro 직렬화 후 발행(㊱ P2). event_type=topic."""
        assert self._serializer is not None, "producer not started"
        env = make_envelope(event_type=topic, payload=value, producer=self._name, key=key)
        avro_obj = {**env.to_dict(), "payload": json.dumps(env.payload, ensure_ascii=False)}
        data = self._serializer(avro_obj, SerializationContext(topic, MessageField.VALUE))
        if data is None:  # payload=None 아님 — 방어
            return
        await asyncio.to_thread(self._publish_sync, topic, data, key)
        logger.info("published topic=%s key=%s event_id=%s", topic, key, env.event_id)


def _decode(deserializer: AvroDeserializer, topic: str, raw: bytes) -> dict[str, Any]:
    """이중 경로 디코딩 — confluent Avro(매직바이트 0) vs 레거시 날 JSON(`{`). payload(도메인)만 반환."""
    if raw and raw[0] == 0:  # confluent Avro 와이어 포맷
        obj = deserializer(raw, SerializationContext(topic, MessageField.VALUE))
        payload = obj.get("payload") if isinstance(obj, dict) else None
        if isinstance(payload, str):
            loaded = json.loads(payload)
            return loaded if isinstance(loaded, dict) else {}
        return payload if isinstance(payload, dict) else {}
    obj = json.loads(raw.decode())  # 레거시 JSON(봉투/날것) 또는 Debezium 아웃박스
    if isinstance(obj, str):  # Debezium이 JSONB payload를 문자열로 이중 인코딩한 경우 방어(㊱ P3)
        obj = json.loads(obj)
    return unwrap(obj)


def _commit_sync(consumer: Consumer, msg: Any) -> None:
    """수동 커밋(동기) — 처리 성공/DLQ 후 offset 전진. to_thread로 격리 호출."""
    consumer.commit(message=msg, asynchronous=False)


async def consume_reliable(
    *,
    topic: str,
    group_id: str,
    bootstrap: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
    retry_max: int = RETRY_MAX,
    dlq_suffix: str = DLQ_SUFFIX,
    schema_registry_url: str = "",
) -> None:
    """수동커밋 소비(㊱ P4, at-least-once) — 성공/DLQ 후에만 offset 커밋.

    실패는 retry_max회 재시도(선형 백오프) 후 `{topic}{dlq_suffix}`로 발행하고 offset 전진
    (poison 메시지가 파티션을 막지 않게). 디코딩 실패도 DLQ. 핸들러엔 payload(도메인)만.
    """
    reg_url = schema_registry_url or _registry_url()
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # 수동커밋 — 처리 성공해야 offset 전진
        }
    )
    deserializer = AvroDeserializer(SchemaRegistryClient({"url": reg_url}), ENVELOPE_AVRO_SCHEMA)
    dlq = KafkaProducer(bootstrap, producer_name=f"{group_id}-dlq", schema_registry_url=reg_url)
    await dlq.start()
    consumer.subscribe([topic])
    logger.info("consuming(reliable) topic=%s group=%s retry_max=%s", topic, group_id, retry_max)
    try:
        while True:
            msg = await asyncio.to_thread(consumer.poll, 1.0)
            if msg is None:
                continue
            if msg.error() is not None:
                logger.warning("consume error topic=%s: %s", topic, msg.error())
                continue
            raw = msg.value()
            if raw is None:
                await asyncio.to_thread(_commit_sync, consumer, msg)
                continue
            raw_bytes = raw if isinstance(raw, bytes) else str(raw).encode()
            mkey = msg.key()
            await _process_one(
                topic, raw_bytes, deserializer, handler, dlq, retry_max, dlq_suffix,
                mkey.decode() if isinstance(mkey, bytes) else None,
            )
            await asyncio.to_thread(_commit_sync, consumer, msg)  # 성공/DLQ 후 전진
    finally:
        await dlq.stop()
        await asyncio.to_thread(consumer.close)


async def _process_one(
    topic: str,
    raw_bytes: bytes,
    deserializer: AvroDeserializer,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
    dlq: "KafkaProducer",
    retry_max: int,
    dlq_suffix: str,
    key: str | None,
) -> None:
    """1건 처리 — 디코딩+핸들러(재시도). 실패 시 DLQ 발행. 예외를 밖으로 던지지 않음(offset 전진)."""
    try:
        payload = _decode(deserializer, topic, raw_bytes)
    except Exception as exc:  # noqa: BLE001 — 디코딩 실패도 DLQ(poison)
        await _to_dlq(dlq, topic, dlq_suffix, {}, f"decode: {exc}", 0, key)
        logger.exception("decode failed → DLQ topic=%s", topic)
        return
    last_err = ""
    for attempt in range(retry_max + 1):
        try:
            await handler(payload)
            return
        except Exception as exc:  # noqa: BLE001 — 재시도 후 DLQ
            last_err = str(exc)
            if attempt < retry_max:
                await asyncio.sleep(_RETRY_BACKOFF * (attempt + 1))
    await _to_dlq(dlq, topic, dlq_suffix, payload, last_err, retry_max + 1, key)
    logger.error("handler failed %sx → DLQ topic=%s err=%s", retry_max + 1, topic, last_err)


async def _to_dlq(
    dlq: "KafkaProducer", topic: str, dlq_suffix: str,
    payload: dict[str, Any], error: str, attempts: int, key: str | None,
) -> None:
    """DLQ 발행 — 원본 payload + 실패 메타(사람 검수·재투입용)."""
    await dlq.publish(
        f"{topic}{dlq_suffix}",
        {
            "original": payload,
            "error": error[:500],
            "attempts": attempts,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "source_topic": topic,
        },
        key=key,
    )


async def consume_forever(
    *,
    topic: str,
    group_id: str,
    bootstrap: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
    schema_registry_url: str = "",
) -> None:
    """소비 진입점 — ㊱ P4로 `consume_reliable`(수동커밋+재시도+DLQ)에 위임(호출부 무변경)."""
    await consume_reliable(
        topic=topic, group_id=group_id, bootstrap=bootstrap, handler=handler,
        schema_registry_url=schema_registry_url,
    )
