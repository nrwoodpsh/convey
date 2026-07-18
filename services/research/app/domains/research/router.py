"""research 라우터.

핵심: agent가 RAG를 위해 호출하는 /search (결정 #4 — agent는 DB 없이 research API 경유).
TODO(/design): 소스 등록·원문 조회 엔드포인트 확정.
"""
from __future__ import annotations

from common.gateway_auth import make_gateway_dep
from common.security import UserContext
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.domains.research import service
from app.domains.research.schemas import SearchResponse

router = APIRouter(prefix="/research", tags=["research"])
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    top_k: int = 4,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """리서치 원문 RAG 검색 — agent가 east-west 호출."""
    return await service.search(session, q, top_k)

# TODO(/design): POST /sources, GET /documents/{id} 등
