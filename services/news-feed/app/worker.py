"""뉴스·공시·거시 수집 워커 → Kafka 발행. ADR 0008 · 라운드⑥.

배포 형태 ②(워커): HTTP 없음. 두 루프를 동시 실행:
  - 뉴스·공시 루프: RSS + Naver 뉴스검색(종목 타깃) + DART 공시 → 태깅 → research.ingested
  - 거시 루프(저빈도): ECOS + FRED → MacroIndicatorEvent → research.macro
research가 소비해 저장(Article·그래프 / MacroIndicator 사실).
"""
from __future__ import annotations

import asyncio
import logging

from common.kafka import KafkaProducer
from common.logging import configure_logging

from app.config import settings
from app.external_client import (
    DartClient,
    EcosClient,
    FredClient,
    NaverNewsClient,
    RssClient,
)
from app.tagging import TICKER_DICT, tag_entity_names, tag_event_hints, tag_tickers

configure_logging(settings.log_level)
logger = logging.getLogger("news-feed")


async def _news_loop(producer: KafkaProducer) -> None:
    """RSS + Naver + DART → research.ingested (기존 주기)."""
    feed_urls = [u.strip() for u in settings.feed_urls.split(",") if u.strip()]
    rss = RssClient(feed_urls)
    naver = NaverNewsClient(settings.naver_client_id, settings.naver_client_secret)
    dart = DartClient(settings.dart_api_key)
    queries = list(TICKER_DICT)  # 종목명으로 타깃 검색
    logger.info(
        "news 루프 feeds=%d naver=%s dart=%s",
        len(feed_urls), bool(settings.naver_client_id), bool(settings.dart_api_key),
    )
    while True:
        docs = rss.fetch() + naver.search(queries) + dart.fetch_recent()
        for doc in docs:
            if not doc.get("source_url"):
                continue  # 가드레일: 무출처 제외
            text = f"{doc['title']} {doc['body']}"
            event = {
                **doc,
                "tickers": tag_tickers(text),
                "entities": tag_entity_names(text),
                "event_hints": tag_event_hints(text),
            }
            await producer.publish(settings.topic_ingested, event, key=doc["source_url"])
        logger.info("research.ingested 발행 %d건", len(docs))
        await asyncio.sleep(settings.poll_interval_seconds)


async def _macro_loop(producer: KafkaProducer) -> None:
    """ECOS + FRED → research.macro (저빈도 주기)."""
    ecos = EcosClient(settings.ecos_api_key)
    fred = FredClient(settings.fred_api_key)
    logger.info(
        "macro 루프 ecos=%s fred=%s", bool(settings.ecos_api_key), bool(settings.fred_api_key)
    )
    while True:
        indicators = ecos.fetch(settings.ecos_indicators) + fred.fetch(settings.fred_indicators)
        for ind in indicators:
            if not ind.get("source_url"):
                continue  # 가드레일
            await producer.publish(settings.topic_macro, ind, key=f"{ind['source']}:{ind['name']}")
        logger.info("research.macro 발행 %d건", len(indicators))
        await asyncio.sleep(settings.macro_poll_interval_seconds)


async def run() -> None:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info("news-feed 시작 (뉴스·공시 + 거시 동시 수집)")
    try:
        await asyncio.gather(_news_loop(producer), _macro_loop(producer))
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
