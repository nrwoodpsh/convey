"""타입 계약 — 개방형 NER 추출 품질: 엔티티 타입 검증 + 스톱워드 보강. 라운드㉞. ADR 0017.

검증: python -m mypy --strict --ignore-missing-imports api-contract-extract-quality.py

배경(§3/§4 학습에서 발견): 개방형 NER이 "노조·노사·이동통신사" 같은 **일반어를 노드로** 만들고,
그게 관계까지 오염("삼성전자 COMPETES 노조"). 원인 = 프롬프트가 엔티티 타입을 요구하나
**반환 타입을 안 받고 버림** + 스톱워드 19개뿐. 엔티티 오염 → 관계 오염(관계는 엔티티 위에 얹힘).

해결: LLM이 엔티티를 {name, type}로 반환 → **허용 타입만 채택**(구조적) + **스톱워드 보강**(안전망).
엔티티가 깨끗해지면 §4 관계도 자동 정화. 하위호환·환각컷(substring)·근거 결속·엣지 5종 불변.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# 허용 엔티티 타입 — 이 밖(조직·일반·기타 등)은 폐기. 기존 상수 재확인.
ENTITY_TYPES: tuple[str, ...] = ("기업", "인물", "사건", "기관", "섹터")
ENTITY_MIN_LEN = 2

# 스톱워드 보강 — 기존 19개 + 일반 조직·집합어(노조·노사·이동통신사 등). (예시, 구현서 확정)
ENTITY_STOPWORDS_ADD: tuple[str, ...] = (
    "노조", "노사", "이동통신사", "정부부처", "지자체", "당국", "업계", "고객", "소비자", "국민",
)


@dataclass
class TypedEntity:
    """LLM이 반환하는 엔티티 — 이름 + 타입. (기존은 이름 문자열만 받았음.)"""

    name: str
    type: str  # ENTITY_TYPES 중 하나여야 채택


class BuildGraphPrompt(Protocol):
    """엔티티를 {name,type}로 반환하도록 출력 형식을 강화.

    형식: {"entities":[{"name":"...","type":"기업|인물|사건|기관|섹터"}], "relations":[...]}
    (기존: entities는 ["..."] 문자열 배열.)
    """

    def __call__(self, text: str) -> str: ...


class ParseGraph(Protocol):
    """관대한 파싱 — {name,type} 객체 우선. 하위호환: 바레 문자열도 허용(type=미상).

    반환 엔티티는 (name, type|None). type=None(레거시/미상)은 기존 경로(substring+스톱워드)로.
    """

    def __call__(self, raw: str) -> tuple[list[TypedEntity], list[object]]: ...


# ── extract_graph 엔티티 채택 규칙(강화) ──
# 기존(㉚/㉛): raw in verify(환각컷) ∧ len≥MIN ∧ not in STOPWORDS  ∨ seed
# 추가(㉞):    타입이 있으면 type ∈ ENTITY_TYPES 여야 채택(조직·일반·기타 폐기).
#             타입이 없으면(레거시) 기존 규칙만(하위호환). 스톱워드는 보강분 포함.
# 관계(§4): subject/object ∈ (채택 엔티티 ∪ seed) — 기존 로직 그대로라, 엔티티 정화 시 관계도 자동 정화.
ENTITY_RULE_NOTE = (
    "채택 = 환각컷(substring) ∧ len≥2 ∧ ¬stopword ∧ (type∈ENTITY_TYPES ∨ type 미상) ∨ seed. "
    "extract_graph 시그니처·반환(Graph)·엣지 5종·근거 결속 불변. 로컬 Ollama만."
)
