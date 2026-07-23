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


class RelationEvidence(TypedDict):
    """그래프 인과 근거(㉕/알파) — research /search relations. 근거=article_id(→source_url)."""

    subject: str
    edge: str
    object: str
    source_url: str
    article_id: int


def _josa(word: str, with_batchim: str, without: str) -> str:
    """한국어 조사 선택 — 끝 글자 받침 유무. 비한글 끝(영문·숫자)은 무받침형."""
    if not word:
        return without
    last = word[-1]
    if "가" <= last <= "힣":
        return with_batchim if (ord(last) - 0xAC00) % 28 != 0 else without
    return without


def _relation_sentence(rel: RelationEvidence) -> str:
    """그래프 관계 근거 → 한국어 문장(사실 관계의 한국어화, 수치·창작 아님). 조사 자동."""
    s, o, edge = rel["subject"], rel["object"], rel["edge"]
    if edge == "AFFECTS":
        return f"{s}{_josa(s, '이', '가')} {o}에 영향"
    if edge == "SUPPLIES":
        return f"{s}{_josa(s, '이', '가')} {o}에 공급"
    if edge == "COMPETES":
        return f"{s}{_josa(s, '과', '와')} {o} 경쟁 구도"
    if edge == "BELONGS_TO":
        return f"{s}{_josa(s, '은', '는')} {o} 관련주"
    if edge == "HAS_EVENT":
        return f"{s}에 {o} 이슈"
    return f"{s}–{o}"


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
    "breaking": {"facts": 1, "relations": 1, "macro": False, "closing": False,
                 "hook": "속보처럼 급박하게 한 문장. 숫자 금지."},
    "analysis": {"facts": 3, "relations": 2, "macro": True, "closing": False,
                 "hook": "주식 쇼츠 도입 문장 1개. 숫자·수치는 쓰지 말 것. 한 문장."},
    "story": {"facts": 2, "relations": 1, "macro": True, "closing": True,
              "hook": "이야기를 여는 도입 문장 1개. 숫자 금지. 한 문장."},
}


def build_script(
    topic: str,
    price: PriceEvidence,
    facts: list[FactEvidence],
    llm: Callable[[str], str],
    macros: list[MacroEvidence] | None = None,
    template: str = "analysis",
    relations: list[RelationEvidence] | None = None,
) -> Script:
    """근거 스크립트 생성 — 수치는 price·macro 슬롯, 관계는 그래프(근거), 연결 문장만 LLM.

    template(㉔): breaking / analysis(기본) / story. relations(㉕/알파): 그래프 인과 →
    'relation' 섹션(예 "삼성전자과(와) SK하이닉스가 경쟁 구도"). 근거=article_id(무출처 폐기).
    """
    macros = macros or []
    relations = relations or []
    tpl = _TEMPLATES.get(template, _TEMPLATES["analysis"])
    n_facts = int(tpl["facts"])  # type: ignore[call-overload]
    n_rels = int(tpl.get("relations", 0))  # type: ignore[call-overload]
    use_macro = bool(tpl["macro"])
    use_closing = bool(tpl["closing"])
    used_facts = facts[:n_facts]
    # 근거(출처) 있는 관계만, 종목 관련 우선(subject/object에 종목명 포함)
    valid_rels = [r for r in relations if r.get("source_url")][:n_rels]

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
    # 관계(인과) 섹션 — 그래프 근거(알파). 수치 없음, 사실 관계만.
    sections.extend(ScriptSection("relation", _relation_sentence(rel)) for rel in valid_rels)
    sections.extend(ScriptSection("fact", fact["text"]) for fact in used_facts)

    citations = [
        Citation(f"{ticker} 종가 {close}원 / 등락률 {change}%", price["source_url"], price["ref_id"]),
        *[Citation(_relation_sentence(r), r["source_url"], r["article_id"]) for r in valid_rels],
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
