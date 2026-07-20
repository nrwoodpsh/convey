"""라운드① 규칙 태깅 검증 — 환각 없음(사전 밖 종목은 태깅 안 됨)이 핵심(알파1)."""
from __future__ import annotations

from app.tagging import tag_event_hints, tag_tickers


def test_tags_only_known_tickers() -> None:
    text = "삼성전자와 SK하이닉스가 반도체 실적을 발표했다. 애플도 언급됐다."
    # 애플은 사전에 없어 태깅되지 않음 — 무출처/환각 방지
    assert tag_tickers(text) == ["005930", "000660"]


def test_no_false_positive_on_unrelated_text() -> None:
    assert tag_tickers("오늘 날씨가 아주 좋다") == []


def test_dedup_and_order_preserved() -> None:
    assert tag_tickers("삼성전자 삼성전자 현대차") == ["005930", "005380"]


def test_event_hints_detected() -> None:
    assert "실적" in tag_event_hints("영업이익이 급증했다")
    assert "급등락" in tag_event_hints("장 초반 상한가")


def test_event_hints_empty_when_none() -> None:
    assert tag_event_hints("특별한 일은 없었다") == []
