"""research 서비스 계층.

책임: 시세·기사 사실 저장(+출처/라이선스 메타 필수), 관계·인과 그래프(Neo4j) 구축,
      agent용 근거 회수(GraphRAG: Cypher traversal + SQL 사실조회). TODO(/design): 흐름 확정.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.research import repository
from app.domains.research.schemas import SearchHit, SearchResponse


async def search(session: AsyncSession, query: str, top_k: int) -> SearchResponse:
    """근거 회수 — 그래프 traversal(관계·인과) + SQL 사실조회를 합쳐 반환.

    agent가 east-west로 호출(결정: research API 경유, 저장소 직접접근 금지). 벡터 유사도 아님.
    """
    # TODO(/builder): Neo4j Cypher(관계) + Postgres SQL(시세·기사 사실) 회수 → 근거 조합
    _ = repository  # 자리표시 (미구현)
    hits: list[SearchHit] = []
    return SearchResponse(hits=hits)
