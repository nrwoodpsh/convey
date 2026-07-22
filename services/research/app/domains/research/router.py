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
from app.domains.research.schemas import ArticleListResponse, SearchResponse
from app.graph.neo4j_repo import GraphRepo

router = APIRouter(prefix="/research", tags=["research"])
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


def get_graph(request: Request) -> GraphRepo:
    return GraphRepo(request.app.state.neo4j)


@router.get("/articles", response_model=ArticleListResponse)
async def articles(
    window_days: int = 1,
    limit: int = 50,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleListResponse:
    """수집 기사 목록(대시보드 선택용, 라운드㉓) — 최근 window_days, 최신순."""
    return await service.list_articles(session, window_days=window_days, limit=min(limit, 200))


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    top_k: int = 4,
    entity: str | None = None,
    ticker: str | None = None,
    hops: int = 2,
    window_days: int | None = None,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
    graph: GraphRepo = Depends(get_graph),
) -> SearchResponse:
    """근거 회수 — 그래프 관계(최대 hops홉) + SQL 사실(window_days 기간) + 가격 근거(ticker 한정)."""
    return await service.search(
        session, graph, q, entity=entity, ticker=ticker,
        top_k=top_k, hops=hops, window_days=window_days,
    )
