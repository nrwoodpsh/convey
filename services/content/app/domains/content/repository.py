"""content 저장소 계층. TODO(/design): 잡·스크립트·자산 CRUD + pgvector 히스토리 검색."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def vector_search(
    session: AsyncSession, embedding: list[float], top_k: int
) -> list[tuple[int, str, float]]:
    """콘텐츠 히스토리 pgvector 검색. TODO(/design): ContentEmbedding 대상 쿼리."""
    raise NotImplementedError("pgvector 검색 미구현 — /builder")
