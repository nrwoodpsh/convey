"""이슈 랭킹 결정론 검증(알파2) — 점수 정렬·윈도우 경계·z-score. now 주입으로 결정론."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.ranking import RankWeights, RollingRanker

BASE = datetime(2026, 7, 20, 12, 0, 0)


def test_ranks_by_change_desc() -> None:
    r = RollingRanker(RankWeights(w_change=1.0, w_volume=0.0, w_news=0.0))
    r.ingest_tick("A", 100, 1000, BASE)
    r.ingest_tick("A", 110, 1000, BASE + timedelta(minutes=10))  # +10%
    r.ingest_tick("B", 100, 1000, BASE)
    r.ingest_tick("B", 102, 1000, BASE + timedelta(minutes=10))  # +2%
    top = r.top(10, 24, BASE + timedelta(minutes=20))
    assert [t.ticker for t in top] == ["A", "B"]
    assert abs(top[0].price_change_pct - 10.0) < 1e-6


def test_news_count_respects_window() -> None:
    r = RollingRanker(RankWeights(w_change=0.0, w_volume=0.0, w_news=1.0))
    r.ingest_news("A", "u1", BASE)
    r.ingest_news("A", "u2", BASE + timedelta(minutes=5))
    r.ingest_news("A", "u3", BASE - timedelta(hours=48))  # 윈도우 밖
    top = r.top(10, 24, BASE + timedelta(minutes=10))
    assert top[0].news_count == 2  # u1·u2 (윈도우 내 유일 url)


def test_news_count_dedup_same_url() -> None:  # ㊲ — 재발행 중복은 1건
    r = RollingRanker(RankWeights(w_change=0.0, w_volume=0.0, w_news=1.0))
    for m in (0, 5, 6):  # 같은 url 3회(5분 재발행 흉내)
        r.ingest_news("A", "same-url", BASE + timedelta(minutes=m))
    top = r.top(10, 24, BASE + timedelta(minutes=10))
    assert top[0].news_count == 1  # 중복 제거 → 폭발 방지


def test_window_excludes_old_ticks() -> None:
    r = RollingRanker()
    r.ingest_tick("A", 100, 1000, BASE - timedelta(hours=48))
    assert r.top(10, 24, BASE) == []


def test_volume_spike_positive_z() -> None:
    r = RollingRanker(RankWeights(w_change=0.0, w_volume=1.0, w_news=0.0))
    for i, v in enumerate([100, 100, 100, 1000]):
        r.ingest_tick("A", 50, v, BASE + timedelta(minutes=i))
    top = r.top(10, 24, BASE + timedelta(minutes=10))
    assert top[0].volume_z > 0
