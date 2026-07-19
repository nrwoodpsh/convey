"""뉴스·RSS 수집 + 종목·사건 태깅 워커 — 주기적으로 피드/외부 API를 수집해 Kafka로 발행.

배포 형태 ②(워커): HTTP 없음, 게이트웨이 뒤 아님. research/issue-detector가 research.ingested를
구독해 소비한다(이벤트 주도). market-feed 원형을 복제·확장(종목·사건 태깅 추가).
"""
from __future__ import annotations

import asyncio
import logging

from common.kafka import KafkaProducer
from common.logging import configure_logging

from app.config import settings
from app.external_client import ResearchSourceClient

configure_logging(settings.log_level)
logger = logging.getLogger("news-feed")


async def run() -> None:
    feed_urls = [u.strip() for u in settings.feed_urls.split(",") if u.strip()]
    client = ResearchSourceClient(
        feed_urls, settings.external_base_url, settings.external_api_key
    )
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info(
        "news-feed 시작 feeds=%s interval=%ss", len(feed_urls), settings.poll_interval_seconds
    )
    try:
        while True:
            docs = await client.fetch_new_documents()
            for doc in docs:
                # TODO(/design): 이벤트 페이로드·중복 제거·key 전략 확정
                await producer.publish(settings.topic_ingested, doc, key=doc.get("source_url"))
            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
