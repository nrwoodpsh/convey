"""research 라우터. GET /research/search — agent 근거 회수(GraphRAG+SQL, east-west 호출).

agent는 저장소 직접접근 없이 이 API만 호출(결정 #4).
TODO(/design): 소스 등록·원문 조회 엔드포인트 확정.
"""
from __future__ import annotations

from common.gateway_auth import make_gateway_dep
from common.security import UserContext
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.domains.research import service
from app.domains.research.schemas import SearchResponse
from app.graph.neo4j_repo import GraphRepo

router = APIRouter(prefix="/research", tags=["research"])
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


def get_graph(request: Request) -> GraphRepo:
    return GraphRepo(request.app.state.neo4j)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    top_k: int = 4,
    entity: str | None = None,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
    graph: GraphRepo = Depends(get_graph),
) -> SearchResponse:
    """근거 회수 — 그래프 관계 + SQL 사실(GraphRAG, 벡터 아님)."""
    return await service.search(session, graph, q, entity=entity, top_k=top_k)
