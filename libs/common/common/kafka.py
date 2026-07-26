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
from typing import Any

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
    return unwrap(json.loads(raw.decode()))  # 레거시 JSON(봉투/날것) 하위호환


async def consume_forever(
    *,
    topic: str,
    group_id: str,
    bootstrap: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
    schema_registry_url: str = "",
) -> None:
    """토픽을 무한 소비하며 handler 호출(payload만). confluent-kafka poll을 스레드로 격리."""
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,  # P4에서 수동커밋+DLQ로 교체
        }
    )
    registry = SchemaRegistryClient({"url": schema_registry_url or _registry_url()})
    deserializer = AvroDeserializer(registry, ENVELOPE_AVRO_SCHEMA)
    consumer.subscribe([topic])
    logger.info("consuming topic=%s group=%s", topic, group_id)
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
                continue
            raw_bytes = raw if isinstance(raw, bytes) else str(raw).encode()
            try:
                payload = _decode(deserializer, topic, raw_bytes)
                await handler(payload)
            except Exception:  # noqa: BLE001 — 워커는 한 메시지 실패로 죽지 않음
                logger.exception("handler failed topic=%s offset=%s", topic, msg.offset())
    finally:
        await asyncio.to_thread(consumer.close)
