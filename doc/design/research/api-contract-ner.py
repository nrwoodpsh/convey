"""
타입 계약 — 엔티티 인식 확대(개방형 NER) + 수집 멱등 + 전량 백필 (라운드㉚)
검증: python -m mypy --strict --ignore-missing-imports api-contract-ner.py

배경: 그래프가 46개 사전에 갇혀 노드 33·관계 69(기사 1,085건 대비 빈약). 로컬 Ollama로
기사에서 **엔티티+관계를 개방형으로 1콜 추출**(사전=고정확 seed와 합집)해 그래프를 채운다.
가드레일: 추출 엔티티는 **본문에 실재(부분문자열 검증)**·관계는 근거(article_id)·엣지 제한(환각 0).
텍스트 LLM은 로컬 Ollama만(가드레일). 수집 멱등으로 같은 기사 재추출(폴링 중복) 방지.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 관계 엣지 어휘(고정) — 이 밖은 폐기(환각 방지). 기존 extract_relations와 동일.
EDGE_TYPES: tuple[str, ...] = ("HAS_EVENT", "AFFECTS", "SUPPLIES", "COMPETES", "BELONGS_TO")

# 엔티티 타입(개방형 NER 대상) — 노드는 :Entity, 종목은 :Stock 라벨(기존). 인물·사건 등은 :Entity.
ENTITY_TYPES: tuple[str, ...] = ("기업", "인물", "사건", "기관", "섹터")

# 일반어·노이즈 필터(엔티티에서 제외) — 최소 스톱워드. 확장은 후속.
ENTITY_STOPWORDS: tuple[str, ...] = (
    "정부", "시장", "기업", "회사", "경제", "산업", "국내", "해외", "우리", "관련", "이번", "오늘",
)
ENTITY_MIN_LEN = 2  # 이보다 짧은 엔티티는 제외


@dataclass
class ExtractedRelation:
    subject: str
    edge: str
    object: str


@dataclass
class ExtractedGraph:
    """개방형 추출 결과(㉚) — 엔티티 + 관계. 한 번의 Ollama 호출로 함께 산출.

    entities: 본문에 실재하는 정규화 엔티티(사전 seed ∪ LLM). relations: 엣지 제한·근거 결속.
    """

    entities: list[str] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)


# ── 정규화/검증 규칙(가드레일 실현) ──
# 1) substring: 추출 엔티티는 반드시 본문에 존재해야 채택(LLM 환각 엔티티 폐기).
# 2) normalize: 공백·괄호·조사 접미 정리, 별칭→대표명(common.stocks 등 seed 우선), dedup.
# 3) noise: ENTITY_STOPWORDS·ENTITY_MIN_LEN 필터.
# 4) relation: subject/object ∈ (검증 엔티티 ∪ seed), edge ∈ EDGE_TYPES, 근거=article_id.

# ── 수집 멱등(중요) ──
# news-feed가 매 폴링 사이클 같은 기사를 재발행 → research가 중복 저장·재추출(NER면 Ollama 낭비).
# research는 source_url 기준으로 **이미 처리한 기사면 skip**(저장·추출 안 함). 신규만 NER.
INGEST_DEDUP_NOTE = "handle_ingested: source_url 존재 시 skip(멱등). 신규 기사만 NER·저장."

# ── 백필 ──
# scripts/backfill-graph.sh / app.backfill --llm : 과거 기사 전량(1,085) extract_graph 재실행.
BACKFILL_NOTE = "backfill --llm: extract_graph로 엔티티+관계 재추출(전량·재개·부하 주의)."
