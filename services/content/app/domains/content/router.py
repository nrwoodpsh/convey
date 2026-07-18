"""content 라우터.

- POST /content/generate : on-demand 생성 요청(트리거 — 결정: on-demand + 자동 둘 다)
- GET  /content/search   : 콘텐츠 히스토리 RAG 검색(agent east-west 호출, 분리 인덱스)
TODO(/design): 잡 조회·승인 엔드포인트 확정.
"""
from __future__ import annotations

from common.gateway_auth import make_gateway_dep
from common.kafka import KafkaProducer
from common.security import UserContext
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.domains.content import service
from app.domains.content.schemas import GenerateRequest, SearchResponse

router = APIRouter(prefix="/content", tags=["content"])
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.producer  # type: ignore[no-any-return]


@router.get("/search", response_model=SearchResponse)
async def search_history(
    q: str,
    top_k: int = 4,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    return await service.search_history(session, q, top_k)


@router.post("/generate", status_code=202)
async def generate(
    payload: GenerateRequest,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
    producer: KafkaProducer = Depends(get_producer),
) -> dict[str, int]:
    job_id = await service.start_generation(session, producer, payload, user.user_id)
    return {"job_id": job_id}

# TODO(/design): GET /content/jobs/{id}, POST /content/{id}/approve 등
