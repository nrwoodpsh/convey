"""뉴스·공시·거시 수집 워커 → Kafka 발행. ADR 0008 · 라운드⑥.

배포 형태 ②(워커): HTTP 없음. 두 루프를 동시 실행:
  - 뉴스·공시 루프: RSS + Naver 뉴스검색(종목 타깃) + DART 공시 → 태깅 → research.ingested
  - 거시 루프(저빈도): ECOS + FRED → MacroIndicatorEvent → research.macro
research가 소비해 저장(Article·그래프 / MacroIndicator 사실).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

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
from app.admin_client import derive_queries, fetch_config, source_enabled
from app.tagging import TICKER_DICT, tag_entity_names, tag_event_hints, tag_tickers

configure_logging(settings.log_level)
logger = logging.getLogger("news-feed")


async def _maybe(enabled: bool, fn: Any, *args: Any) -> list[dict[str, Any]]:
    """소스 토글(㉝ P3) — enabled면 스레드로 수집, 아니면 빈 목록."""
    if not enabled:
        return []
    result: list[dict[str, Any]] = await asyncio.to_thread(fn, *args)
    return result


async def _news_loop(producer: KafkaProducer) -> None:
    """RSS + Naver + DART → research.ingested. 검색어·소스는 admin 설정(㉝ P3), 실패 시 폴백."""
    feed_urls = [u.strip() for u in settings.feed_urls.split(",") if u.strip()]
    rss = RssClient(feed_urls)
    naver = NaverNewsClient(settings.naver_client_id, settings.naver_client_secret)
    dart = DartClient(settings.dart_api_key)
    fallback_queries = list(TICKER_DICT)  # admin 불가 시 하드코딩 폴백
    logger.info("news 루프 시작 (검색어·소스는 admin /admin/config)")
    while True:
        cfg = await asyncio.to_thread(fetch_config)  # 운영자 설정(admin ㉝ P3)
        if cfg:
            queries = derive_queries(cfg) or fallback_queries
            use_rss, use_naver, use_dart = (
                source_enabled(cfg, "rss"), source_enabled(cfg, "naver"),
                source_enabled(cfg, "dart"),
            )
        else:  # 폴백: 하드코딩 종목·전 소스 ON
            queries, use_rss, use_naver, use_dart = fallback_queries, True, True, True
        rss_docs, naver_docs, dart_docs = await asyncio.gather(
            _maybe(use_rss, rss.fetch),
            _maybe(use_naver, naver.search, queries),
            _maybe(use_dart, dart.fetch_recent),
        )
        docs = rss_docs + naver_docs + dart_docs
        for doc in docs:
            if not doc.get("source_url"):
                continue  # 가드레일: 무출처 제외
            title, body = str(doc["title"]), str(doc["body"])
            event = {
                **doc,
                "tickers": tag_tickers(title, body),       # 제목 우선 + 본문 조건(㉜)
                "entities": tag_entity_names(title, body),
                "event_hints": tag_event_hints(f"{title} {body}"),
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
        # 동기 httpx 호출을 스레드로 — 이벤트 루프 비블로킹 + 병렬 수집
        ecos_rows, fred_rows = await asyncio.gather(
            asyncio.to_thread(ecos.fetch, settings.ecos_indicators),
            asyncio.to_thread(fred.fetch, settings.fred_indicators),
        )
        indicators = ecos_rows + fred_rows
        for ind in indicators:
            if not ind.get("source_url"):
                continue  # 가드레일
            await producer.publish(settings.topic_macro, ind, key=f"{ind['source']}:{ind['name']}")
        logger.info("research.macro 발행 %d건", len(indicators))
        await asyncio.sleep(settings.macro_poll_interval_seconds)


async def run() -> None:
    producer = KafkaProducer(settings.kafka_bootstrap, producer_name="news-feed")
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
