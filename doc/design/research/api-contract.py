"""
API 계약 — 라운드 ①: research (데이터 기반) · ADR 0004·0005·0006
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

담는 것:
 1) 그래프 노드/엣지 타입 (Neo4j research_graph)
 2) 사실 엔티티 형태 (Postgres research_db: Article·PriceTick) — 벡터 없음(ADR 0006)
 3) GET /research/search — agent 근거 회수(GraphRAG: 그래프 traversal + SQL 사실)
 4) 이벤트: market.ticks(market-feed), research.ingested(news-feed)
 5) 에러 레지스트리
가드레일: 회수 결과·관계는 **출처 URL 동반**(무출처 금지). 관계추출은 근거 기사에 결속.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── 1) 그래프 타입 (Neo4j research_graph) ─────────────────
class NodeLabel(str, Enum):
    STOCK = "Stock"
    EVENT = "Event"
    SECTOR = "Sector"
    COMPANY = "Company"  # 기업/인물(협력사·CEO 등)


class EdgeType(str, Enum):
    HAS_EVENT = "HAS_EVENT"    # Stock → Event
    AFFECTS = "AFFECTS"        # Event → Stock (인과·수혜)
    SUPPLIES = "SUPPLIES"      # Company → Company (공급망)
    COMPETES = "COMPETES"      # Stock ↔ Stock (경쟁)
    BELONGS_TO = "BELONGS_TO"  # Stock → Sector (소속)


# ── 2) 사실 엔티티 (Postgres research_db) ─────────────────
class Article(BaseModel):
    id: int
    title: str
    body: str
    source_url: str = Field(description="가드레일: 필수")
    license: str = Field(description="가드레일: 필수")
    published_at: datetime  # UTC
    lang: str = "ko"


class PriceTick(BaseModel):
    ticker: str
    ts: datetime  # UTC
    open: float
    high: float
    low: float
    close: float
    volume: int


# ── 3) GET /research/search (근거 회수, agent east-west) ──
SEARCH_ENDPOINT = ("GET", "/research/search")


class SearchReq(BaseModel):
    q: str = Field(min_length=1, max_length=200)
    ticker: str | None = Field(default=None, description="종목 한정(선택)")
    hops: int = Field(default=2, ge=1, le=3, description="그래프 traversal 깊이")
    top_k: int = Field(default=4, ge=1, le=20)
    window_days: int | None = Field(default=None, ge=1, description="사실 회수 기간(선택)")


class FactHit(BaseModel):
    kind: str  # 'article' | 'price'
    text: str
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int
    published_at: datetime | None = None


class RelationHit(BaseModel):
    subject: str  # 노드 식별자(예: 종목명/티커)
    edge: EdgeType
    object: str
    source_article_id: int  # 이 관계를 뒷받침하는 기사(근거 결속)
    source_url: str  # 가드레일


class SearchRes(BaseModel):
    query: str
    entity: str | None  # 해석된 주요 종목/엔티티
    facts: list[FactHit] = Field(default_factory=list)
    relations: list[RelationHit] = Field(default_factory=list)


# ── 4) 이벤트 계약 ────────────────────────────────────────
TOPIC_MARKET_TICKS = "market.ticks"  # market-feed 발행 → research·issue-detector 구독
TOPIC_RESEARCH_INGESTED = "research.ingested"  # news-feed 발행 → research·issue-detector 구독


class MarketTickEvent(BaseModel):
    ticker: str
    ts: datetime  # UTC
    close: float
    volume: int
    source: str = "KIS"


class ResearchIngestedEvent(BaseModel):
    article_id: int
    source_url: str  # 가드레일
    license: str  # 가드레일
    published_at: datetime  # UTC
    tickers: list[str] = Field(default_factory=list, description="규칙/사전 태깅된 종목")
    event_hints: list[str] = Field(default_factory=list, description="사건 후보(실적·공시 등)")


# ── 5) 에러 레지스트리 (libs/common/common/errors.py와 정합) ──
class ResearchError(tuple[str, int, str], Enum):
    INVALID_PARAM = ("RES001", 400, "요청 파라미터가 유효하지 않습니다.")
    ENTITY_NOT_FOUND = ("RES002", 404, "해당 종목/엔티티를 찾을 수 없습니다.")
