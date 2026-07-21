"""research 도메인 Pydantic 스키마 — 계약(api-contract.py)과 정합. 근거 회수(GraphRAG+SQL)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FactHit(BaseModel):
    kind: str  # 'article' | 'price'
    text: str
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int


class RelationHit(BaseModel):
    subject: str
    edge: str
    object: str
    source_article_id: int
    source_url: str  # 가드레일


class PriceEvidence(BaseModel):
    ticker: str
    close: float
    change_pct: float  # 직전 거래일 대비 등락률(%)
    series: list[float] = Field(default_factory=list)  # 차트용 종가 시계열(정확 값)
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int  # PriceTick id


class MacroHit(BaseModel):
    name: str
    value: float
    unit: str = ""
    as_of: datetime  # UTC
    source: str  # 'ECOS' | 'FRED'
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int  # MacroIndicator id


class SearchResponse(BaseModel):
    query: str
    entity: str | None = None
    facts: list[FactHit] = Field(default_factory=list)
    relations: list[RelationHit] = Field(default_factory=list)
    price: PriceEvidence | None = None  # ticker 한정 시 가격 근거(라운드⑤)
    macros: list[MacroHit] = Field(default_factory=list)  # 거시 맥락(각 name별 최신, 라운드⑦)
