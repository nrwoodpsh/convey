"""타입 계약 — 지식 그래프 온톨로지 확장(서비스급). 라운드㉟. ADR 0018.

검증: python -m mypy --strict --ignore-missing-imports api-contract-ontology.py

배경: 현 온톨로지(5노드·5엣지)는 최소라 서비스에 부족 — 협력·계열·수혜/타격·인수·제품·테마·
정책·공시유형(유상증자 등)·방향(증가/감소)을 못 담음. §4 점검에서 엣지 오용(HAS_EVENT→섹터)도 발견.

확장: 노드 9종·엣지 12종 + 사건 속성(event_type·direction) + **엣지 domain/range 제약**(양끝 타입 검증).
㉞(엔티티 타입검증 + 엣지-양끝 제약)을 흡수·확장. 환각컷·근거 결속·로컬 Ollama·seed 신뢰 불변.
정량 수치(주문량·가동률)는 그래프 아님 → Postgres(사실). 그래프는 정성 이벤트·관계만.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

# ── 노드 타입 (5 → 9) ──
ENTITY_TYPES: tuple[str, ...] = (
    "기업", "인물", "사건", "기관", "섹터",          # 기존
    "제품", "테마", "정책", "국가",                  # 확장
)

# ── 엣지 타입 (5 → 12) ──
EDGE_TYPES: tuple[str, ...] = (
    "BELONGS_TO", "HAS_EVENT", "COMPETES", "SUPPLIES", "AFFECTS",   # 기존
    "PARTNERS_WITH", "AFFILIATE_OF", "BENEFITS_FROM", "HURT_BY",    # 확장(협력·계열·수혜·타격)
    "PRODUCES", "ACQUIRES", "REGULATES",                            # 확장(생산·인수·규제)
)

# ── 엣지 domain/range 제약 (주어 타입 → 목적어 타입) — §4 엣지 오용 차단 ──
# 값이 빈 tuple이면 "제한 없음"(AFFECTS 같은 일반 영향). 위반 삼중항은 폐기.
EDGE_DOMAIN_RANGE: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "BELONGS_TO":    (("기업",), ("섹터",)),
    "HAS_EVENT":     (("기업",), ("사건",)),
    "COMPETES":      (("기업",), ("기업",)),
    "SUPPLIES":      (("기업",), ("기업",)),
    "AFFECTS":       ((), ()),  # 일반 영향 — 제한 없음(방향 필요하면 BENEFITS_FROM/HURT_BY)
    "PARTNERS_WITH": (("기업",), ("기업",)),
    "AFFILIATE_OF":  (("기업",), ("기업",)),
    "BENEFITS_FROM": (("기업",), ("정책", "사건", "테마")),
    "HURT_BY":       (("기업",), ("정책", "사건")),
    "PRODUCES":      (("기업",), ("제품",)),
    "ACQUIRES":      (("기업",), ("기업",)),
    "REGULATES":     (("기관",), ("기업", "섹터")),
}

# ── 사건(Event) 속성 — 새 노드/엣지 대신 속성으로(폭발 방지) ──
EVENT_TYPES: tuple[str, ...] = (
    "실적", "유상증자", "무상증자", "자사주", "배당", "감자", "인수합병",
    "수주", "신제품", "증설", "소송", "파업", "급등락",
)
Direction = Literal["긍정", "부정", "중립"]  # 호재/악재/중립(수혜↔타격, 증가↔감소 매핑)


@dataclass
class TypedEntity:
    """엔티티 — 이름 + 타입(ENTITY_TYPES). 사건이면 event_type·direction 부가."""

    name: str
    type: str
    event_type: str = ""       # type=="사건"일 때만 의미(EVENT_TYPES)
    direction: Direction | None = None  # 방향(호재/악재) — 있으면


@dataclass
class TypedRelation:
    subject: str
    edge: str
    object: str


# ── 추출·검증 규칙(확장) ──
class BuildGraphPrompt(Protocol):
    """확장 온톨로지를 반환하도록 프롬프트 강화 — 노드 타입 9·엣지 12·event_type·direction 예시 포함."""

    def __call__(self, text: str) -> str: ...


# extract_graph 엔티티/관계 채택(확장):
#  엔티티: 환각컷(substring) ∧ len≥2 ∧ ¬stopword ∧ (type∈ENTITY_TYPES ∨ type 미상)  ∨ seed
#  관계:   subject/object ∈ 채택엔티티∪seed ∧ edge∈EDGE_TYPES
#          ∧ **양끝 타입이 EDGE_DOMAIN_RANGE[edge]에 부합**(빈 tuple=무제한)  ← §4 오용 차단
#  사건:   event_type∈EVENT_TYPES(속성), direction∈Direction(옵션) → :Entity 속성으로 저장
RULE_NOTE = (
    "엣지 domain/range 위반(예: HAS_EVENT의 목적어가 섹터) 폐기. extract_graph 시그니처·반환(Graph) "
    "골격 유지(엔티티에 type/event_type/direction 부가). 결정론 엣지(섹터·사건)·근거 결속·로컬 Ollama 불변."
)
