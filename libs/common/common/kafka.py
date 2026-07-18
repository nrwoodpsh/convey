"""aiokafka 기반 발행/소비 헬퍼 (JSON 직렬화)."""
from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaProducer:
    """서비스 수명주기에 붙여 쓰는 프로듀서 래퍼."""

    def __init__(self, bootstrap: str) -> None:
        self._bootstrap = bootstrap
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
        assert self._producer is not None, "producer not started"
        await self._producer.send_and_wait(topic, value=value, key=key)
        logger.info("published topic=%s key=%s", topic, key)


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
                await handler(msg.value)
            except Exception:  # noqa: BLE001 — 워커는 한 메시지 실패로 죽지 않음
                logger.exception("handler failed offset=%s", msg.offset)
    finally:
        await consumer.stop()
