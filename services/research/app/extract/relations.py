"""LLM 관계추출 — 하이브리드 추출의 'LLM 절반'. 라운드①.

기사 + 규칙 태깅된 엔티티 → (subject, edge, object) 관계 후보를 로컬 LLM으로 추출.
환각 방지: (1) 프롬프트로 허용 엔티티·정해진 엣지타입만 요구, (2) 결과에서 허용 밖은 폐기.
LLM은 주입(테스트=스텁, 운영=llm-inference→Ollama). 수치는 만들지 않음(사실은 Postgres).
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

EDGE_TYPES: tuple[str, ...] = ("HAS_EVENT", "AFFECTS", "SUPPLIES", "COMPETES", "BELONGS_TO")


@dataclass
class Relation:
    subject: str
    edge: str
    object: str


def build_prompt(text: str, allowed_entities: list[str]) -> str:
    ents = ", ".join(allowed_entities)
    edges = ", ".join(EDGE_TYPES)
    return (
        "다음 기사에서 엔티티 간 관계만 JSON 배열로 추출하라.\n"
        f"허용 엔티티: {ents}\n"
        f"허용 엣지: {edges}\n"
        '형식: [{"subject":"...","edge":"...","object":"..."}]\n'
        "허용 엔티티/엣지만 사용. 없으면 []. 설명 없이 JSON만 출력.\n\n"
        f"기사:\n{text}"
    )


def _parse(raw: str) -> list[Relation]:
    """LLM 응답에서 JSON 배열만 관대하게 파싱(설명·<think> 등 감싸도 추출)."""
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    out: list[Relation] = []
    for item in data:
        if isinstance(item, dict) and {"subject", "edge", "object"} <= item.keys():
            out.append(Relation(str(item["subject"]), str(item["edge"]), str(item["object"])))
    return out


def extract_relations(
    text: str, allowed_entities: list[str], llm: Callable[[str], str]
) -> list[Relation]:
    """LLM 추출 → 허용 엔티티·엣지로 필터. 허용 밖 엔티티·엣지는 폐기(환각 방지)."""
    allowed = set(allowed_entities)
    candidates = _parse(llm(build_prompt(text, allowed_entities)))
    return [
        r
        for r in candidates
        if r.subject in allowed and r.object in allowed and r.edge in EDGE_TYPES
    ]


# ── 개방형 NER(엔티티+관계 1콜, 라운드㉚) — 계약 api-contract-ner.py ──
ENTITY_TYPES: tuple[str, ...] = ("기업", "인물", "사건", "기관", "섹터")
ENTITY_STOPWORDS: frozenset[str] = frozenset({
    "정부", "시장", "기업", "회사", "경제", "산업", "국내", "해외", "우리", "관련", "이번",
    "오늘", "내년", "올해", "사업", "서비스", "기술", "투자", "실적",
})
ENTITY_MIN_LEN = 2


@dataclass
class Graph:
    """개방형 추출 결과 — 엔티티 + 관계(㉚)."""

    entities: list[str]
    relations: list[Relation]


def _normalize_entity(name: str) -> str:
    """엔티티 표기 정리 — 공백·감싼 따옴표/괄호 제거. (완전 개체연결은 후속.)"""
    n = name.strip().strip("'\"“”()[]{}〈〉《》").strip()
    return n


def build_graph_prompt(text: str) -> str:
    types = ", ".join(ENTITY_TYPES)
    edges = ", ".join(EDGE_TYPES)
    return (
        "다음 기사에서 엔티티와 관계를 JSON 객체로 추출하라.\n"
        f"엔티티 종류: {types}. 반드시 기사에 실제로 나온 표현만.\n"
        f"허용 엣지: {edges}.\n"
        '형식: {"entities":["..."],"relations":[{"subject":"...","edge":"...","object":"..."}]}\n'
        "기사에 없는 것은 만들지 말 것. 설명 없이 JSON만 출력.\n\n"
        f"기사:\n{text}"
    )


def _parse_graph(raw: str) -> tuple[list[str], list[Relation]]:
    """LLM 응답에서 {entities, relations} JSON 객체를 관대하게 파싱."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return [], []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], []
    ents = [str(e) for e in data.get("entities", []) if isinstance(e, str)]
    rels: list[Relation] = []
    for item in data.get("relations", []):
        if isinstance(item, dict) and {"subject", "edge", "object"} <= item.keys():
            rels.append(Relation(str(item["subject"]), str(item["edge"]), str(item["object"])))
    return ents, rels


def extract_graph(
    text: str, seed_entities: list[str], llm: Callable[[str], str]
) -> Graph:
    """개방형 추출(㉚) — 엔티티+관계 1콜. 환각 통제: 본문 실재(substring)·정규화·스톱워드·엣지 제한.

    seed_entities(사전=고정확)는 검증 없이 신뢰(news-feed가 본문 매칭으로 뽑음). LLM 엔티티는 검증.
    """
    raw_ents, raw_rels = _parse_graph(llm(build_graph_prompt(text)))
    verified: dict[str, str] = {}  # normalized → canonical
    for e in raw_ents:
        raw = e.strip()
        if raw and raw in text:  # 환각컷: 본문에 실재해야 채택
            n = _normalize_entity(raw)
            if len(n) >= ENTITY_MIN_LEN and n not in ENTITY_STOPWORDS:
                verified[n] = n
    # 사전 seed 합집(seed는 이미 본문 매칭 — 고정확)
    for s in seed_entities:
        verified[s] = s
    allowed = set(verified)
    rels = [
        Relation(r.subject.strip(), r.edge, r.object.strip())
        for r in raw_rels
        if r.subject.strip() in allowed and r.object.strip() in allowed and r.edge in EDGE_TYPES
    ]
    return Graph(entities=sorted(allowed), relations=rels)
