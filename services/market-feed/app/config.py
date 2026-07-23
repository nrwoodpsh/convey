from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    topic_ticks: str = "market.ticks"
    poll_interval_seconds: float = 60.0  # KRX 일봉은 자주 안 바뀜 — 폴링 완만
    # CSV — 주요 종목 확대(㉙/E2). 전체 마스터는 common.stocks(gen-stocks.py). 폴링 부담 고려해 상위군.
    symbols: str = (
        "005930,000660,005380,000270,373220,006400,051910,035420,035720,"
        "005490,105560,055550,207940,068270,012330,066570"
    )

    # pykrx 조회 창(일수) — 휴장·주말 대비 넉넉히 잡고 최신 거래일 1건 사용
    lookback_days: int = 30


settings = Settings()
