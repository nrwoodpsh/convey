"""research 저장소 계층. TODO(/design): CRUD + pgvector 유사도 검색 쿼리."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def vector_search(
    session: AsyncSession, embedding: list[float], top_k: int
) -> list[tuple[int, str, str, float]]:
    """pgvector 코사인 유사도 top_k 검색.

    TODO(/design): Embedding 테이블에 대해
        ORDER BY embedding <=> :query_vec LIMIT :top_k
    쿼리 구현. 반환 (document_id, text, source_url, score).
    """
    raise NotImplementedError("pgvector 검색 미구현 — /builder")
