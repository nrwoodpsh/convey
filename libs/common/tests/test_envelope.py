"""이벤트 봉투 검증(㊱ P1) — wrap 메타 생성·unwrap payload 추출·레거시 하위호환."""
from __future__ import annotations

from common.envelope import ENVELOPE_VERSION, is_envelope, unwrap, wrap


def test_wrap_has_metadata() -> None:
    env = wrap("research.ingested", {"source_url": "https://n/1"}, producer="news-feed", key="k")
    assert env["event_type"] == "research.ingested"
    assert env["version"] == ENVELOPE_VERSION
    assert env["producer"] == "news-feed"
    assert env["key"] == "k"
    assert env["payload"] == {"source_url": "https://n/1"}
    assert env["event_id"] and "T" in env["occurred_at"]  # UUID + ISO8601


def test_unwrap_returns_payload() -> None:
    env = wrap("t", {"a": 1}, producer="p")
    assert unwrap(env) == {"a": 1}


def test_unwrap_legacy_raw_json() -> None:
    """봉투 아닌 레거시 날 JSON은 그대로 통과(전환·재생 안전)."""
    raw = {"ticker": "005930", "close": 71900}
    assert unwrap(raw) == raw
    assert is_envelope(raw) is False


def test_event_ids_unique() -> None:
    a = wrap("t", {}, producer="p")
    b = wrap("t", {}, producer="p")
    assert a["event_id"] != b["event_id"]  # 추적·중복제거 열쇠
