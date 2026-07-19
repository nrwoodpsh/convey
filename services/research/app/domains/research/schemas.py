"""research 도메인 Pydantic 스키마. TODO(/design): 필드 확정."""
from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    """agent 근거 회수 결과 1건(GraphRAG+SQL). TODO(/design): 관계경로·source_url 등 확정."""

    article_id: int
    text: str
    source_url: str
    relevance: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
