"""근거 스크립트 빌더 검증(알파1) — 수치는 데이터에서만, 모든 항목 출처 결속.

핵심 테스트: LLM이 거짓 숫자를 뱉어도 스크립트 수치는 사실(price)에서만 온다(환각 물리 차단).
"""
from __future__ import annotations

from app.script.builder import ScenarioKnobs, build_script

PRICE = {
    "ticker": "삼성전자", "close": 71900, "change_pct": 2.34,
    "source_url": "https://kis/1", "ref_id": 10,
}
FACTS = [
    {"text": "삼성전자 반도체 호실적", "source_url": "https://news/1", "ref_id": 1},
    {"text": "메모리 가격 반등", "source_url": "https://news/2", "ref_id": 2},
    {"text": "파운드리 수주 확대", "source_url": "https://news/3", "ref_id": 3},
]
MACROS = [{"name": "원달러환율(매매기준율)", "value": 1350.0, "unit": "원",
           "source_url": "https://ecos/1", "ref_id": 20}]


def test_numbers_come_from_data_not_llm() -> None:
    # LLM이 "종가 99999원"이라 해도 슬롯 수치는 입력 price에서만
    script = build_script("삼성전자", PRICE, FACTS, lambda _: "무조건 종가 99999원 급등!!")
    chart = next(s for s in script.sections if s.kind == "chart")
    assert chart.data_slots["close"] == "71,900"  # 데이터값(표기 정리, ㉗) — LLM의 99999 아님
    assert chart.data_slots["change_pct"] == "+2.34"


def test_every_citation_has_source() -> None:
    script = build_script("삼성전자", PRICE, FACTS, lambda _: "도입 문장")
    assert script.citations
    assert all(c.source_url for c in script.citations)  # 무출처 0 (가드레일)


def test_hook_is_llm_prose_without_slots() -> None:
    script = build_script("삼성전자", PRICE, FACTS, lambda _: "오늘의 화제 종목")
    hook = next(s for s in script.sections if s.kind == "hook")
    assert hook.text == "오늘의 화제 종목"
    assert hook.data_slots == {}  # 도입엔 수치 슬롯 없음


# ── 시나리오 템플릿 노브(㊳) ──
def _n_facts(script: object) -> int:
    return sum(1 for s in script.sections if s.kind == "fact")  # type: ignore[attr-defined]


def test_knobs_change_structure() -> None:
    """AC3 — 다른 노브 → 다른 구조(사실 개수·거시·마무리). 속보형은 사실 1·거시 없음."""
    breaking = ScenarioKnobs(1, 1, False, False, "속보 톤")
    story = ScenarioKnobs(2, 1, True, True, "이야기 톤")
    sb = build_script("삼성전자", PRICE, FACTS, lambda _: "문장", MACROS, breaking)
    ss = build_script("삼성전자", PRICE, FACTS, lambda _: "문장", MACROS, story)
    assert _n_facts(sb) == 1 and _n_facts(ss) == 2       # 사실 수 노브 반영
    assert not any(s.kind == "macro" for s in sb.sections)  # 속보형: 거시 없음
    assert any(s.kind == "macro" for s in ss.sections)      # 스토리형: 거시 있음
    assert not any(s.kind == "closing" for s in sb.sections)  # 속보형: 마무리 없음
    assert any(s.kind == "closing" for s in ss.sections)      # 스토리형: 마무리 있음


def test_default_knobs_is_analysis() -> None:
    """AC4 — knobs 미지정 시 기본(분석형): 사실 3·거시 있음·마무리 없음(기존 회귀)."""
    s = build_script("삼성전자", PRICE, FACTS, lambda _: "문장", MACROS)
    assert _n_facts(s) == 3
    assert any(x.kind == "macro" for x in s.sections)
    assert not any(x.kind == "closing" for x in s.sections)
