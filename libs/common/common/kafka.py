"""aiokafka 기반 발행/소비 헬퍼 (JSON 직렬화) — 이벤트 봉투(㊱ P1) 표준.

발행: payload를 EventEnvelope로 감싸(event_id·type·version·occurred_at·producer) JSON 직렬화.
소비: consume_forever가 봉투를 자동 언랩해 핸들러엔 payload(도메인 데이터)만 넘긴다(핸들러 무변경).
하위호환: 레거시 날 JSON 메시지도 unwrap이 그대로 통과시킨다(전환·재생 안전).
"""
from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from common.envelope import unwrap, wrap

logger = logging.getLogger(__name__)


class KafkaProducer:
    """서비스 수명주기에 붙여 쓰는 프로듀서 래퍼. producer_name은 봉투의 발행자 메타."""

    def __init__(self, bootstrap: str, producer_name: str = "unknown") -> None:
        self._bootstrap = bootstrap
        self._name = producer_name
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            enable_idempotence=True,
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def publish(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        """payload를 봉투로 감싸 발행(㊱ P1). event_type=topic, Kafka 파티션 키는 그대로."""
        assert self._producer is not None, "producer not started"
        envelope = wrap(event_type=topic, payload=value, producer=self._name, key=key)
        await self._producer.send_and_wait(topic, value=envelope, key=key)
        logger.info("published topic=%s key=%s event_id=%s", topic, key, envelope["event_id"])


async def consume_forever(
    *,
    topic: str,
    group_id: str,
    bootstrap: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """토픽을 무한 소비하며 handler 호출. 워커 진입점에서 await."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode()),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("consuming topic=%s group=%s", topic, group_id)
    try:
        async for msg in consumer:
            try:
                await handler(unwrap(msg.value))  # 봉투 언랩(㊱ P1) — 핸들러엔 payload만
            except Exception:  # noqa: BLE001 — 워커는 한 메시지 실패로 죽지 않음
                logger.exception("handler failed offset=%s", msg.offset)
    finally:
        await consumer.stop()
