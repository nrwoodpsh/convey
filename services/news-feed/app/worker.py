"""뉴스·공시 수집 + 종목·사건 태깅 워커 → research.ingested 발행. ADR 0008.

배포 형태 ②(워커): HTTP 없음. RSS(무료)·DART(공시, 무료키)를 수집 → 규칙 태깅 →
`ResearchIngestedEvent`(title·body·출처·tickers·entities·event_hints) 발행.
research가 소비해 저장+관계추출+그래프. (원형 market-feed 패턴 확장)
"""
from __future__ import annotations

import asyncio
import logging

from common.kafka import KafkaProducer
from common.logging import configure_logging

from app.config import settings
from app.external_client import DartClient, RssClient
from app.tagging import tag_entity_names, tag_event_hints, tag_tickers

configure_logging(settings.log_level)
logger = logging.getLogger("news-feed")


async def run() -> None:
    feed_urls = [u.strip() for u in settings.feed_urls.split(",") if u.strip()]
    rss = RssClient(feed_urls)
    dart = DartClient(settings.dart_api_key)
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info("news-feed 시작 feeds=%s dart=%s", len(feed_urls), bool(settings.dart_api_key))
    try:
        while True:
            docs = rss.fetch() + dart.fetch_recent()
            for doc in docs:
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
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
