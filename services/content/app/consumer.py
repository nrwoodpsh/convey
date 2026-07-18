"""content Kafka 소비 루프 — API 서비스에 붙는 consumer(원형에 없던 패턴, 갭#5).

content는 HTTP API인 동시에 `content.generate`(및 미디어 완료 이벤트)를 구독해야 한다.
lifespan에서 이 소비 루프를 백그라운드 태스크로 띄우고, 종료 시 취소한다.
TODO(/design): 구독 토픽 집합(generate + image/tts/video 완료)·join 방식·핸들러 확정.
"""
from __future__ import annotations

import logging
from typing import Any

from common.kafka import consume_forever

from app.config import settings

logger = logging.getLogger("content.consumer")


async def handle_generate(event: dict[str, Any]) -> None:
    """content.generate 수신 → 생성 잡 시작. TODO(/builder): service.start_generation 연결."""
    logger.info("content.generate 수신: %s", event)
    # TODO(/builder): 잡 시작·단계 진행


async def run_consumer() -> None:
    """lifespan 백그라운드 태스크 진입점."""
    await consume_forever(
        topic=settings.topic_generate,
        group_id=settings.consumer_group,
        bootstrap=settings.kafka_bootstrap,
        handler=handle_generate,
    )
    # TODO(/design): 미디어 완료 토픽(image/tts/video)도 함께 구독해 fan-in 처리
