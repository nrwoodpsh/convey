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


# 공시(DART)는 별도 엔티티 없이 Article(원문+출처=DART 링크) + Event(사건)로 흡수 (ADR 0008)
class MacroIndicator(BaseModel):
    """거시 지표(ECOS·FRED) — 사실. 금리·환율·물가 등. 스크립트 맥락·이슈 신호. (ADR 0008)"""

    name: str  # 예: '기준금리' · '원달러환율' · 'CPI'
    value: float
    unit: str = ""
    as_of: datetime  # UTC
    source: str  # 'ECOS' | 'FRED'
    source_url: str  # 가드레일: 출처 필수


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


class PriceEvidence(BaseModel):
    """가격 근거 — 최신 종가·등락률·시계열(PriceTick 사실). 스크립트·차트에 공급(라운드⑤)."""

    ticker: str
    close: float
    change_pct: float  # 직전 거래일 대비 등락률(%)
    series: list[float] = Field(default_factory=list)  # 차트용 종가 시계열(정확 값)
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int  # PriceTick id


class SearchRes(BaseModel):
    query: str
    entity: str | None  # 해석된 주요 종목/엔티티
    facts: list[FactHit] = Field(default_factory=list)
    relations: list[RelationHit] = Field(default_factory=list)
    price: PriceEvidence | None = None  # ticker 한정 시 가격 근거(라운드⑤)


# ── 4) 이벤트 계약 ────────────────────────────────────────
TOPIC_MARKET_TICKS = "market.ticks"  # market-feed 발행 → research·issue-detector 구독
TOPIC_RESEARCH_INGESTED = "research.ingested"  # news-feed 발행 → research·issue-detector 구독


class MarketTickEvent(BaseModel):
    ticker: str
    ts: datetime  # UTC (거래일)
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = "KRX"  # pykrx(무료·키X) 실측 — ADR 0008 (KIS 제외)


class ResearchIngestedEvent(BaseModel):
    title: str
    body: str  # 원문 — research가 Article 저장 + LLM 관계추출에 사용
    source_url: str  # 가드레일
    license: str  # 가드레일
    published_at: datetime  # UTC
    tickers: list[str] = Field(default_factory=list, description="규칙 태깅된 종목 코드")
    entities: list[str] = Field(
        default_factory=list, description="규칙 매칭된 엔티티 이름(관계추출 allowed)"
    )
    event_hints: list[str] = Field(default_factory=list, description="사건 후보(실적·공시 등)")


# 거시 지표(ECOS·FRED) 발행 — news-feed(거시 루프) → research 저장(MacroIndicator). 라운드⑥ (ADR 0008)
TOPIC_RESEARCH_MACRO = "research.macro"


class MacroIndicatorEvent(BaseModel):
    """거시 사실 1건. MacroIndicator(사실 모델)과 1:1. 그래프 미경유(Postgres 사실)."""

    name: str  # 예: '한국은행 기준금리' · '원달러환율' · '연방기금금리'
    value: float
    unit: str = ""  # 예: '연%' · '원'
    as_of: datetime  # UTC (지표 기준시점)
    source: str  # 'ECOS' | 'FRED'
    source_url: str  # 가드레일: 무출처 금지


# ── 5) 에러 레지스트리 (libs/common/common/errors.py와 정합) ──
class ResearchError(tuple[str, int, str], Enum):
    INVALID_PARAM = ("RES001", 400, "요청 파라미터가 유효하지 않습니다.")
    ENTITY_NOT_FOUND = ("RES002", 404, "해당 종목/엔티티를 찾을 수 없습니다.")
