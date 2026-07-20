"""content 라우터 — 생성 잡 라이프사이클 + 히스토리 조회.

- POST /content/generate       : 생성 요청 → 잡(pending) + content.generate 발행
- GET  /content/jobs/{job_id}  : 잡 상태 조회
- POST /content/jobs/{job_id}/approve : 사람 승인(ready→approved) → content.approved
- GET  /content/search         : 히스토리 조회(agent east-west)
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
from app.domains.content.schemas import GenerateRequest, JobRes, SearchResponse

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


@router.get("/jobs/{job_id}", response_model=JobRes)
async def get_job(
    job_id: int,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> JobRes:
    return await service.get_job(session, job_id)


@router.post("/jobs/{job_id}/approve", response_model=JobRes)
async def approve(
    job_id: int,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
    producer: KafkaProducer = Depends(get_producer),
) -> JobRes:
    return await service.approve(session, producer, job_id)
