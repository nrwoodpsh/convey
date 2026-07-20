"""근거 스크립트 빌더 — 템플릿 + 사실 슬롯 + LLM 연결문장. 알파1 (환각 물리 차단). 라운드③.

핵심: 수치(종가·등락률)는 **사실 데이터에서만** `data_slots`로 주입한다. LLM은 연결 문장(prose)만
생성하고 숫자를 만들지 않는다. 모든 수치·사실은 `Citation`(출처)에 결속(무출처 금지).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypedDict


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


def build_script(
    topic: str,
    price: PriceEvidence,
    facts: list[FactEvidence],
    llm: Callable[[str], str],
) -> Script:
    """근거 스크립트 생성 — 수치는 price에서만 슬롯으로, 연결 문장만 LLM. 모든 항목 출처 결속."""
    ticker = price["ticker"]
    close = str(price["close"])
    change = f"{price['change_pct']:.2f}"

    # 연결 문장(LLM) — 숫자 없이 prose만. 수치는 아래 chart 슬롯에서만.
    hook = llm(f"'{topic}' 주식 쇼츠 도입 문장 1개. 숫자·수치는 쓰지 말 것. 한 문장.").strip()

    sections = [
        ScriptSection("hook", hook),
        ScriptSection(
            "chart",
            f"{ticker} 종가 {{close}}원, 등락률 {{change_pct}}%",
            {"ticker": ticker, "close": close, "change_pct": change},
        ),
    ]
    sections.extend(ScriptSection("fact", fact["text"]) for fact in facts)

    citations = [
        Citation(f"{ticker} 종가 {close}원 / 등락률 {change}%", price["source_url"], price["ref_id"]),
        *[Citation(fact["text"], fact["source_url"], fact["ref_id"]) for fact in facts],
    ]
    return Script(sections=sections, citations=citations)
