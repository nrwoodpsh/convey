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
