"""issue-detector 스트림 소비 — market.ticks·research.ingested → RollingRanker. 라운드②.

DB 직접접속 없이 Kafka 스트림만 소비(경계 유지). 랭킹 상태는 프로세스 내(재기동 시 재구축).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from common.kafka import KafkaProducer, consume_forever

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


async def run_emitter(ranker: RollingRanker) -> None:
    """자동 양산(알파4) — 주기적으로 상위 이슈를 issue.selected로 발행. content가 자동 생성.

    score 임계 + 상위 K + 종목 쿨다운으로 무의미·중복 양산을 막는다.
    """
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    cooldown: dict[str, datetime] = {}
    logger.info(
        "issue emitter 시작 interval=%ss top_k=%s thr=%s",
        settings.emit_interval_seconds, settings.emit_top_k, settings.score_threshold,
    )
    try:
        while True:
            now = datetime.now(timezone.utc)
            for r in ranker.top(settings.emit_top_k, settings.window_hours, now):
                if r.score < settings.score_threshold:
                    continue
                last = cooldown.get(r.ticker)
                if last and (now - last).total_seconds() < settings.cooldown_seconds:
                    continue  # 스로틀: 쿨다운 내 재발행 억제
                await producer.publish(
                    settings.topic_issue_selected,
                    {"ticker": r.ticker, "name": "", "score": r.score, "as_of": now.isoformat()},
                    key=r.ticker,
                )
                cooldown[r.ticker] = now
                logger.info("issue.selected 발행 ticker=%s score=%.2f", r.ticker, r.score)
            await asyncio.sleep(settings.emit_interval_seconds)
    finally:
        await producer.stop()
