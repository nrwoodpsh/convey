"""research 저장소 계층(Postgres 사실). TODO(/design): Article·PriceTick CRUD + 사실 조회 쿼리.

관계·인과 그래프(Neo4j)는 별도 그래프 리포지토리(round① /builder)에서 다룬다.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def fact_search(
    session: AsyncSession, query: str, top_k: int
) -> list[tuple[int, str, str]]:
    """사실 조회 — ticker·기간·키워드로 Article·PriceTick 회수(SQL 인덱스). 벡터 아님.

    TODO(/design): Article(원문+출처)·PriceTick(시세) 대상 쿼리 구현.
    반환 (article_id, text, source_url).
    """
    raise NotImplementedError("사실 조회 미구현 — /builder")
