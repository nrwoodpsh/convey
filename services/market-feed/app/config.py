from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    topic_ticks: str = "market.ticks"
    poll_interval_seconds: float = 60.0  # KRX 일봉은 자주 안 바뀜 — 폴링 완만
    symbols: str = "005930,000660,035420"  # CSV (예: 삼성전자·SK하이닉스·NAVER)

    # pykrx 조회 창(일수) — 휴장·주말 대비 넉넉히 잡고 최신 거래일 1건 사용
    lookback_days: int = 30


settings = Settings()
