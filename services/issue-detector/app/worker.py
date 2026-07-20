"""issue-detector 스트림 소비 — market.ticks·research.ingested → RollingRanker. 라운드②.

DB 직접접속 없이 Kafka 스트림만 소비(경계 유지). 랭킹 상태는 프로세스 내(재기동 시 재구축).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from common.kafka import consume_forever

from app.config import settings
from app.ranking import RollingRanker

logger = logging.getLogger("issue-detector")


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now(timezone.utc)


async def run_consumers(ranker: RollingRanker) -> None:
    """두 스트림을 동시 소비해 랭커 상태를 갱신(백그라운드)."""

    async def on_tick(event: dict[str, Any]) -> None:
        ranker.ingest_tick(
            event["ticker"], float(event["close"]), int(event["volume"]), _parse_ts(event.get("ts"))
        )

    async def on_news(event: dict[str, Any]) -> None:
        ts = _parse_ts(event.get("published_at"))
        for ticker in event.get("tickers", []):
            ranker.ingest_news(ticker, ts)

    await asyncio.gather(
        consume_forever(
            topic=settings.topic_ticks,
            group_id=f"{settings.consumer_group}-ticks",
            bootstrap=settings.kafka_bootstrap,
            handler=on_tick,
        ),
        consume_forever(
            topic=settings.topic_ingested,
            group_id=f"{settings.consumer_group}-news",
            bootstrap=settings.kafka_bootstrap,
            handler=on_news,
        ),
    )
