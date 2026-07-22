"""근거 스크립트 빌더 — 템플릿 + 사실 슬롯 + LLM 연결문장. 알파1 (환각 물리 차단). 라운드③.

핵심: 수치(종가·등락률)는 **사실 데이터에서만** `data_slots`로 주입한다. LLM은 연결 문장(prose)만
생성하고 숫자를 만들지 않는다. 모든 수치·사실은 `Citation`(출처)에 결속(무출처 금지).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypedDict

from common.stocks import stock_name


class PriceEvidence(TypedDict):
    ticker: str
    close: float
    change_pct: float
    source_url: str
    ref_id: int


class FactEvidence(TypedDict):
    text: str
    source_url: str
    ref_id: int


class MacroEvidence(TypedDict):
    name: str
    value: float
    unit: str
    source_url: str
    ref_id: int


@dataclass
class Citation:
    claim: str
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int


@dataclass
class ScriptSection:
    kind: str  # 'hook' | 'chart' | 'fact' | 'closing'
    text: str
    data_slots: dict[str, str] = field(default_factory=dict)


@dataclass
class Script:
    sections: list[ScriptSection] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)


# 시나리오 템플릿(구성·톤 3종, ㉔) — 기사 선택 후 사용자가 고름.
# 사용 사실 개수·거시 포함·마무리(closing) 여부·훅 문체를 달리한다. 기본 analysis(회귀 0).
_TEMPLATES: dict[str, dict[str, object]] = {
    "breaking": {"facts": 1, "macro": False, "closing": False,
                 "hook": "속보처럼 급박하게 한 문장. 숫자 금지."},
    "analysis": {"facts": 3, "macro": True, "closing": False,
                 "hook": "주식 쇼츠 도입 문장 1개. 숫자·수치는 쓰지 말 것. 한 문장."},
    "story": {"facts": 2, "macro": True, "closing": True,
              "hook": "이야기를 여는 도입 문장 1개. 숫자 금지. 한 문장."},
}


def build_script(
    topic: str,
    price: PriceEvidence,
    facts: list[FactEvidence],
    llm: Callable[[str], str],
    macros: list[MacroEvidence] | None = None,
    template: str = "analysis",
) -> Script:
    """근거 스크립트 생성 — 수치는 price·macro 슬롯에서만, 연결 문장만 LLM. 모든 항목 출처 결속.

    template(㉔): breaking(속보·짧게) / analysis(분석·기본, 회귀 0) / story(도입-전개-마무리).
    macros(거시 맥락)는 선택 — 비면 기존과 동일. 거시 수치도 슬롯에서만(환각 차단).
    """
    macros = macros or []
    tpl = _TEMPLATES.get(template, _TEMPLATES["analysis"])
    n_facts = int(tpl["facts"])  # type: ignore[call-overload]
    use_macro = bool(tpl["macro"])
    use_closing = bool(tpl["closing"])
    used_facts = facts[:n_facts]

    ticker = price["ticker"]
    close = str(price["close"])
    change = f"{price['change_pct']:.2f}"
    # 종목은 코드가 아니라 한글명으로 노출(㉓ — 시나리오·내레이션·자막에서 코드 낭독 제외).
    # 사전 밖이면 접두 생략(없는 이름 지어내지 않음 — 환각 금지).
    name = stock_name(ticker)
    stock_prefix = f"{name} " if name else ""

    # 연결 문장(LLM) — 숫자 없이 prose만. 수치는 아래 chart 슬롯에서만.
    hook = llm(f"'{topic}' {tpl['hook']}").strip()

    sections = [
        ScriptSection("hook", hook),
        ScriptSection(
            "chart",
            f"{stock_prefix}종가 {{close}}원, 등락률 {{change_pct}}%",
            {"ticker": ticker, "close": close, "change_pct": change},
        ),
    ]
    sections.extend(ScriptSection("fact", fact["text"]) for fact in used_facts)

    citations = [
        Citation(f"{ticker} 종가 {close}원 / 등락률 {change}%", price["source_url"], price["ref_id"]),
        *[Citation(fact["text"], fact["source_url"], fact["ref_id"]) for fact in used_facts],
    ]

    # 거시 맥락 섹션 — 수치는 macro 슬롯에서만(사실), LLM 미개입.
    if use_macro and macros:
        slots = {m["name"]: f"{m['value']} {m['unit']}".strip() for m in macros}
        summary = ", ".join(f"{m['name']} {slots[m['name']]}" for m in macros)
        sections.append(ScriptSection("macro", f"거시 맥락 — {summary}", slots))
        citations.extend(
            Citation(f"{m['name']} {slots[m['name']]}", m["source_url"], m["ref_id"])
            for m in macros
        )

    # 스토리형 마무리(전망) — 숫자 없는 연결 문장(LLM), 근거 결속 없음(전망 문장).
    if use_closing:
        closing = llm(f"'{topic}' 쇼츠를 닫는 전망 한 문장. 숫자 금지. 단정 금지.").strip()
        if closing:
            sections.append(ScriptSection("closing", closing))

    return Script(sections=sections, citations=citations)
