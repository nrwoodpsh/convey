"""규칙 태깅 검증 — 환각 없음(사전 밖 제외) + 제목 우선·본문 조건 오탐 차단(㉜, 알파1)."""
from __future__ import annotations

from app.tagging import tag_entity_names, tag_event_hints, tag_tickers


def test_entity_names_only_known() -> None:
    # 제목에 종목명 → 태깅. 애플(사전 밖) 제외.
    assert tag_entity_names("삼성전자와 SK하이닉스 언급, 애플도", "") == ["삼성전자", "SK하이닉스"]


def test_tags_only_known_tickers() -> None:
    assert tag_tickers("삼성전자와 SK하이닉스 반도체 실적, 애플도", "") == ["005930", "000660"]


def test_no_false_positive_on_unrelated_text() -> None:
    assert tag_tickers("오늘 날씨가 아주 좋다", "") == []


def test_dedup_and_order_preserved() -> None:
    assert tag_tickers("삼성전자 삼성전자 현대차", "") == ["005930", "005380"]


# ── ㉜ 제목 우선 + 본문 조건 ──
def test_title_match_tags() -> None:  # AC1 — 제목에 종목명이면 태깅
    assert "005380" in tag_tickers("현대차 노조 파업", "본문 내용")


def test_body_single_mention_not_tagged() -> None:  # AC2 — 본문 1회 스침은 미태깅
    # 제목엔 카카오 없음, 본문에 '카카오톡' 1회 → 카카오(035720) 태깅 안 됨
    assert "035720" not in tag_tickers("경동나비엔 보일러 A/S 1위", "카카오톡 채널을 구축했다")


def test_body_repeated_mention_tagged() -> None:  # AC3 — 본문 2회 이상은 태깅
    assert "005930" in tag_tickers("업계 동향", "삼성전자가 발표했다. 삼성전자는 또 밝혔다.")


def test_substring_suppressed() -> None:  # AC4 회귀 — SK ⊂ SK하이닉스
    assert tag_tickers("SK하이닉스 실적", "") == ["000660"]


def test_event_hints_detected() -> None:
    assert "실적" in tag_event_hints("영업이익이 급증했다")
    assert "급등락" in tag_event_hints("장 초반 상한가")


def test_event_hints_empty_when_none() -> None:
    assert tag_event_hints("특별한 일은 없었다") == []
