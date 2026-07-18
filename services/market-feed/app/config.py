from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    topic_ticks: str = "market.ticks"
    poll_interval_seconds: float = 2.0
    symbols: str = "005930,000660,035420"  # CSV (예: 삼성전자·SK하이닉스·NAVER)

    # 실제 KIS 연동 시 사용 (지금은 mock)
    external_base_url: str = "https://openapi.koreainvestment.com:9443"
    kis_app_key: str = ""
    kis_app_secret: str = ""


settings = Settings()
