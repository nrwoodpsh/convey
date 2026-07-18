"""content 도메인 Pydantic 스키마. TODO(/design): 필드 확정."""
from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """on-demand 생성 요청. TODO(/design): 주제·소스 범위·콘텐츠 유형 등 확정."""

    topic: str


class SearchHit(BaseModel):
    """콘텐츠 히스토리 RAG 검색 결과 1건."""

    content_id: int
    text: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
