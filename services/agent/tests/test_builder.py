"""근거 스크립트 빌더 검증(알파1) — 수치는 데이터에서만, 모든 항목 출처 결속.

핵심 테스트: LLM이 거짓 숫자를 뱉어도 스크립트 수치는 사실(price)에서만 온다(환각 물리 차단).
"""
from __future__ import annotations

from app.script.builder import build_script

PRICE = {
    "ticker": "삼성전자", "close": 71900, "change_pct": 2.34,
    "source_url": "https://kis/1", "ref_id": 10,
}
FACTS = [{"text": "삼성전자 반도체 호실적", "source_url": "https://news/1", "ref_id": 1}]


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
