"""admin 관심목록 연동 검증(㉝ P4) — 활성 종목 티커 집합 도출."""
from __future__ import annotations

from app.admin_client import watchlist_tickers


def test_watchlist_tickers() -> None:
    cfg = {"stocks": [{"ticker": "005930"}, {"ticker": "000660"}], "keywords": []}
    assert watchlist_tickers(cfg) == {"005930", "000660"}


def test_watchlist_empty() -> None:
    assert watchlist_tickers({}) == set()
    assert watchlist_tickers({"stocks": []}) == set()
