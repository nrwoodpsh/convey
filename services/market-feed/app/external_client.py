"""외부 시세 소스 클라이언트 (부패방지 계층) — pykrx(무료·키X). ADR 0008.

pykrx는 KRX 공개 데이터를 조회한다(인증키 불필요). 여기서 외부 스키마(DataFrame·
한글 컬럼)를 내부 표준 tick 딕트로 변환·격리한다. pykrx 호출은 **동기·블로킹**이므로
워커에서 `asyncio.to_thread`로 감싸 이벤트 루프를 막지 않는다.

가드레일: 산출 tick에 source(KRX)를 기록. 값 조작·추정 금지 — 최신 거래일 실측만.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from pykrx import stock

logger = logging.getLogger("market-feed")


class KrxMarketClient:
    """KRX 일봉(OHLCV) 실측 조회 — 인증키 없음."""

    def __init__(self, lookback_days: int = 30) -> None:
        self._lookback_days = lookback_days

    def latest_ohlcv(self, ticker: str, today: date) -> dict[str, Any] | None:
        """최근 창에서 마지막 거래일 1건을 실측으로 반환.

        휴장·주말·공휴일을 감안해 `lookback_days` 창을 조회하고 가장 마지막 행을 쓴다.
        데이터가 없으면(상장폐지·잘못된 티커·미개장) None → 워커가 스킵.
        """
        fromdate = (today - timedelta(days=self._lookback_days)).strftime("%Y%m%d")
        todate = today.strftime("%Y%m%d")
        df = stock.get_market_ohlcv(fromdate, todate, ticker)
        if df is None or df.empty:
            logger.warning("KRX OHLCV 없음 ticker=%s [%s~%s]", ticker, fromdate, todate)
            return None
        row = df.iloc[-1]
        ts = df.index[-1]  # pandas Timestamp (거래일)
        return {
            "ticker": ticker,
            "ts": ts.strftime("%Y-%m-%dT00:00:00+00:00"),
            "open": float(row["시가"]),
            "high": float(row["고가"]),
            "low": float(row["저가"]),
            "close": float(row["종가"]),
            "volume": int(row["거래량"]),
            "source": "KRX",
        }
