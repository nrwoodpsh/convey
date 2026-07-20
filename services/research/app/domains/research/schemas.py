"""research 도메인 Pydantic 스키마 — 계약(api-contract.py)과 정합. 근거 회수(GraphRAG+SQL)."""
from __future__ import annotations

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


class SearchResponse(BaseModel):
    query: str
    entity: str | None = None
    facts: list[FactHit] = Field(default_factory=list)
    relations: list[RelationHit] = Field(default_factory=list)
