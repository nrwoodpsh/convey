"""content 서비스 계층 — 생성 잡 상태머신. 라운드③.

start_generation: 잡 생성(pending) → content.generate 발행(consumer 픽업). approve: ready→approved
→ content.approved 발행(사람 승인 후에만 — 가드레일). 히스토리 조회는 중복회피(키워드/메타).
"""
from __future__ import annotations

from common.errors import AppError
from common.kafka import KafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.content import repository
from app.domains.content.models import GenerationJob
from app.domains.content.schemas import GenerateRequest, JobRes, JobStatus, SearchResponse


def _to_res(job: GenerationJob) -> JobRes:
    return JobRes(
        job_id=job.id, status=job.status, script_id=job.script_id,
        content_id=job.content_id, error=job.error,
    )


async def start_generation(
    session: AsyncSession, producer: KafkaProducer, req: GenerateRequest, owner_id: str
) -> int:
    """생성 잡 시작 — 잡(pending) 커밋 후 content.generate 발행(비동기 consumer 픽업)."""
    job = GenerationJob(
        status=JobStatus.PENDING.value, topic=req.topic, ticker=req.ticker, owner_id=owner_id
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await producer.publish(
        settings.topic_generate,
        {"job_id": job.id, "topic": req.topic, "ticker": req.ticker},
        key=str(job.id),
    )
    return job.id


async def get_job(session: AsyncSession, job_id: int) -> JobRes:
    job = await session.get(GenerationJob, job_id)
    if job is None:
        raise AppError("CNT002", "잡을 찾을 수 없습니다.", status=404)
    return _to_res(job)


async def approve(session: AsyncSession, producer: KafkaProducer, job_id: int) -> JobRes:
    """사람 승인 — ready 상태만 approved로. content.approved 발행(발행 파이프라인 트리거)."""
    job = await session.get(GenerationJob, job_id)
    if job is None:
        raise AppError("CNT002", "잡을 찾을 수 없습니다.", status=404)
    if job.status != JobStatus.READY.value:
        raise AppError("CNT003", "승인 가능한 상태가 아닙니다.", status=409)
    job.status = JobStatus.APPROVED.value
    await session.commit()
    await session.refresh(job)
    await producer.publish(
        settings.topic_approved,
        {"job_id": job.id, "content_id": job.content_id},
        key=str(job.id),
    )
    return _to_res(job)


async def search_history(session: AsyncSession, query: str, top_k: int) -> SearchResponse:
    """콘텐츠 히스토리 조회 — 중복회피(키워드/메타). 벡터 아님(ADR 0006)."""
    _ = repository  # 자리표시 (구현: history_search)
    return SearchResponse(hits=[])
