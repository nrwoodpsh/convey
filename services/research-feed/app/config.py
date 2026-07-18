from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # 발행: 수집 원문 → research/content 구독
    topic_ingested: str = "research.ingested"

    poll_interval_seconds: float = 300.0  # 피드 폴링 주기 (TODO(/design): 소스별로 확정)

    # 리서치 소스 — TODO(/design): RSS 피드 URL 목록 + 외부 API 설정
    feed_urls: str = ""  # CSV of RSS/Atom feed URLs
    external_base_url: str = ""
    external_api_key: str = ""


settings = Settings()
