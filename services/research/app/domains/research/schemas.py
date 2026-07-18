"""research 도메인 Pydantic 스키마. TODO(/design): 필드 확정."""
from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    """agent RAG 검색 결과 1건. TODO(/design): score·source_url·chunk 등 확정."""

    document_id: int
    text: str
    source_url: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
