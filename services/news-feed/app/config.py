from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # 발행: 수집 원문 → research/issue-detector 구독
    topic_ingested: str = "research.ingested"

    poll_interval_seconds: float = 300.0  # 피드 폴링 주기

    # 소스 (ADR 0008): 공개 뉴스 RSS(키 없음) CSV + DART 공시(무료 키)
    feed_urls: str = "https://www.yna.co.kr/rss/economy.xml,https://www.hankyung.com/feed/economy"
    dart_api_key: str = ""  # opendart.fss.or.kr 발급(무료). 없으면 공시 스킵


settings = Settings()
