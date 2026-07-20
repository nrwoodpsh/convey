"""이슈 종목 랭킹 — 시세 변동성 + 뉴스 빈도 가중합. 알파2. 라운드②.

market.ticks·research.ingested 스트림을 **프로세스 내 롤링 윈도우**로 집계(DB 없음 — 경계 유지).
score = w_change*|등락률| + w_volume*volume_z + w_news*news_count
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, pstdev


@dataclass
class RankWeights:
    w_change: float = 0.5
    w_volume: float = 0.3
    w_news: float = 0.2


@dataclass
class _TickerState:
    ticks: list[tuple[datetime, float, int]] = field(default_factory=list)  # (ts, close, volume)
    news: list[datetime] = field(default_factory=list)


@dataclass
class IssueRank:
    ticker: str
    score: float
    price_change_pct: float
    volume_z: float
    news_count: int


class RollingRanker:
    """스트림 이벤트를 받아 윈도우 기준 이슈 랭킹을 계산. 순수 로직(테스트에 now 주입)."""

    def __init__(self, weights: RankWeights | None = None) -> None:
        self._w = weights or RankWeights()
        self._state: dict[str, _TickerState] = {}

    def ingest_tick(self, ticker: str, close: float, volume: int, ts: datetime) -> None:
        self._state.setdefault(ticker, _TickerState()).ticks.append((ts, close, volume))

    def ingest_news(self, ticker: str, ts: datetime) -> None:
        self._state.setdefault(ticker, _TickerState()).news.append(ts)

    def _metrics(self, st: _TickerState, since: datetime) -> tuple[float, float, int] | None:
        ticks = [(ts, c, v) for (ts, c, v) in st.ticks if ts >= since]
        news_count = sum(1 for ts in st.news if ts >= since)
        if not ticks and news_count == 0:
            return None
        change_pct = 0.0
        volume_z = 0.0
        if ticks:
            closes = [c for (_, c, _) in ticks]
            first, last = closes[0], closes[-1]
            change_pct = (last - first) / first * 100 if first else 0.0
            vols = [float(v) for (_, _, v) in ticks]
            if len(vols) >= 2:
                sd = pstdev(vols)
                volume_z = (vols[-1] - mean(vols)) / sd if sd else 0.0
        return change_pct, volume_z, news_count

    def top(self, top_k: int, window_hours: int, now: datetime) -> list[IssueRank]:
        since = now - timedelta(hours=window_hours)
        out: list[IssueRank] = []
        for ticker, st in self._state.items():
            metrics = self._metrics(st, since)
            if metrics is None:
                continue
            change_pct, volume_z, news_count = metrics
            score = (
                self._w.w_change * abs(change_pct)
                + self._w.w_volume * volume_z
                + self._w.w_news * news_count
            )
            out.append(IssueRank(ticker, score, change_pct, volume_z, news_count))
        out.sort(key=lambda r: r.score, reverse=True)
        return out[:top_k]
