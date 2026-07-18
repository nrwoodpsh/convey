"""research 서비스 계층.

책임: 소스 수집 원문 저장(+출처/라이선스 메타 필수), 임베딩 생성(로컬 Ollama),
      agent용 RAG 검색(pgvector). TODO(/design): 흐름 확정.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.research import repository
from app.domains.research.schemas import SearchHit, SearchResponse


async def search(session: AsyncSession, query: str, top_k: int) -> SearchResponse:
    """질의 → 임베딩 → pgvector 검색. agent가 east-west로 호출(결정: research API 경유)."""
    # TODO(/builder): query 임베딩(embedding_model) → repository.vector_search
    _ = repository  # 자리표시 (미구현)
    hits: list[SearchHit] = []
    return SearchResponse(hits=hits)
