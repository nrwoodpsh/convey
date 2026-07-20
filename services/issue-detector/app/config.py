from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # 구독 스트림 (research 계약의 이벤트) — DB 직접접속 없이 Kafka만 (경계 유지)
    topic_ticks: str = "market.ticks"
    topic_ingested: str = "research.ingested"
    consumer_group: str = "issue-detector"

    # 랭킹 (알파2) — score = w_change*|등락률| + w_volume*volume_z + w_news*news_count
    window_hours: int = 24
    w_change: float = 0.5
    w_volume: float = 0.3
    w_news: float = 0.2


settings = Settings()
