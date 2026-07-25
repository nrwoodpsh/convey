"""타입 계약 — 이슈 선별 news_count 중복 제거. 라운드㊲.

검증: python -m mypy --strict --ignore-missing-imports api-contract-issue-dedup.py

배경(§6 학습에서 실측): 삼성전자 score 812(정상 18) — `ingest_news`가 재발행 중복 기사를
매번 +1 카운트 → news_count 폭발 → 랭킹 왜곡(알파②). research는 source_url로 걸러 저장하나
issue-detector는 안 걸러 카운트. 해결: **윈도우 내 source_url 유일 건만 카운트**(멱등).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class _TickerState:
    """(변경) news를 시각 리스트 → source_url별 최신 시각 dict(중복 제거)."""

    ticks: list[tuple[datetime, float, int]] = field(default_factory=list)
    news: dict[str, datetime] = field(default_factory=dict)  # source_url → ts (유일)


class IngestNews(Protocol):
    """(변경) 시그니처에 source_url 추가 — 같은 source_url 재수신은 카운트 안 늘림(최신 ts만 갱신).

    (기존) ingest_news(ticker, ts) → (신규) ingest_news(ticker, source_url, ts).
    news_count = 윈도우 내 **유일 source_url 수**.
    """

    def __call__(self, ticker: str, source_url: str, ts: datetime) -> None: ...


# ── 배선 ──
# worker.py: research.ingested 소비 시 event["source_url"]을 ingest_news에 전달.
# ranking.py _metrics: news_count = sum(1 for ts in st.news.values() if ts >= since)
NOTE = "score 공식·가중치·임계(0.5)·윈도우(24h) 불변. 중복만 제거 → 폭발 해소. DB 없음(메모리) 유지."
