"""publishing 소비 — content.approved → 발행 큐잉 + YouTube 업로드. 라운드⑤ (알파4).

멱등 상태머신(service) + YouTube 부패방지(youtube)가 핵심. 발행은 **사람 승인(content.approved) 후에만**.
전송·업로드 e2e는 Kafka·OAuth 준비 시(핵심 멱등 로직은 검증됨).
"""
from __future__ import annotations

import logging
from typing import Any

from common.kafka import consume_forever

from app import service
from app.config import settings
from app.db import SessionLocal
from app.youtube import YouTubeClient

logger = logging.getLogger("publishing.consumer")


async def run_consumer() -> None:
    yt = YouTubeClient(settings.youtube_token)

    async def handler(event: dict[str, Any]) -> None:
        content_id = event.get("content_id")
        if content_id is None:
            logger.warning("content.approved에 content_id 없음: %s", event)
            return
        async with SessionLocal() as session:
            await service.enqueue(session, int(content_id))  # 멱등
            try:
                url = await yt.upload(f"{content_id}.mp4", title=f"content {content_id}")
                await service.mark_published(session, int(content_id), url)
            except NotImplementedError as exc:  # 토큰·연결 전 — 실패로 기록(재시도 가능)
                await service.mark_failed(session, int(content_id), str(exc))

    await consume_forever(
        topic=settings.topic_approved,
        group_id=settings.consumer_group,
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )
