"""content 서비스 계층 — 생성 잡 상태머신. 라운드③.

start_generation: 잡 생성(pending) → content.generate 발행(consumer 픽업). approve: ready→approved
→ content.approved 발행(사람 승인 후에만 — 가드레일). 히스토리 조회는 중복회피(키워드/메타).
"""
from __future__ import annotations

from common.errors import AppError
from common.kafka import KafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.content import media, repository
from app.domains.content.models import GenerationJob
from app.domains.content.outbox import publish_via_outbox
from app.domains.content.schemas import (
    GenerateRequest,
    JobRes,
    JobStatus,
    SearchHit,
    SearchResponse,
)


def _to_res(job: GenerationJob) -> JobRes:
    return JobRes(
        job_id=job.id, status=job.status, script_id=job.script_id,
        content_id=job.content_id, error=job.error,
    )


async def start_generation(
    session: AsyncSession,
    producer: KafkaProducer,
    req: GenerateRequest,
    owner_id: str,
    *,
    auto: bool = True,
    template_id: int | None = None,
) -> int:
    """생성 잡 시작 — 잡(pending) 커밋 후 content.generate 발행(비동기 consumer 픽업).

    auto=True(자동양산): 스크립트 후 합성까지 무정지. auto=False(대시보드 수동, ㉓): 스크립트
    생성 후 scenario_ready에서 정지 → 사람이 승인해야 합성(approve_scenario).
    template_id(㊳): admin_db 시나리오 템플릿 id — consumer가 노브를 조회해 agent로 전달(없으면 기본형).
    """
    job = GenerationJob(
        status=JobStatus.PENDING.value, topic=req.topic, ticker=req.ticker, owner_id=owner_id
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await producer.publish(
        settings.topic_generate,
        {"job_id": job.id, "topic": req.topic, "ticker": req.ticker,
         "auto": auto, "template_id": template_id},
        key=str(job.id),
    )
    return job.id


async def update_script(
    session: AsyncSession, job_id: int, sections: list[dict[str, str]]
) -> JobRes:
    """시나리오 수정 저장(㉔) — scenario_ready인 잡의 Script 섹션 텍스트를 편집본으로 갱신.

    kind 순서로 매칭해 text만 교체(차트 data_slots·수치는 보존 — 알파3). 합성 시작 후엔 잠금(CNT003).
    """
    job = await session.get(GenerationJob, job_id)
    if job is None:
        raise AppError("CNT002", "잡을 찾을 수 없습니다.", status=404)
    if job.status != JobStatus.SCENARIO_READY.value:
        raise AppError("CNT003", "수정 가능한 상태가 아닙니다.", status=409)
    script = await repository.get_script_by_job(session, job_id)
    if script is None:
        raise AppError("CNT002", "시나리오를 찾을 수 없습니다.", status=404)
    # 편집본을 인덱스 순서대로 반영(text만). 길이 초과분은 무시, 부족분은 원본 유지.
    edited = list(sections)
    new_sections = []
    for i, sec in enumerate(script.sections):
        text = edited[i]["text"] if i < len(edited) else str(sec.get("text", ""))
        new_sections.append({**sec, "text": text})
    script.sections = new_sections
    await session.commit()
    return _to_res(job)


async def approve_scenario(
    session: AsyncSession, producer: KafkaProducer, job_id: int, *, background: str = "real"
) -> JobRes:
    """시나리오 승인(㉓·㉔) — scenario_ready만 → 보존한 chart+편집본으로 media.assemble → assembling.

    수동 흐름의 사람 게이트(영상 만들기 전). background=real(산업)|anim(모션그래픽). 자동양산은 미경유.
    """
    job = await session.get(GenerationJob, job_id)
    if job is None:
        raise AppError("CNT002", "잡을 찾을 수 없습니다.", status=404)
    if job.status != JobStatus.SCENARIO_READY.value:
        raise AppError("CNT003", "승인 가능한 상태가 아닙니다.", status=409)
    if not job.chart:
        raise AppError("CNT003", "차트 근거가 없어 승인할 수 없습니다.", status=409)
    script = await repository.get_script_by_job(session, job_id)
    sections = script.sections if script is not None else []
    citations = script.citations if script is not None else []
    event = media.build_assemble_event(
        job_id=job_id, topic=job.topic, ticker=job.ticker,
        chart=job.chart, sections=sections,
        narration_max_chars=settings.narration_max_chars,
        background=background,
        citations=citations,
        date=job.created_at.date().isoformat(),
    )
    job.status = JobStatus.ASSEMBLING.value
    await session.commit()
    await session.refresh(job)
    await producer.publish(settings.topic_assemble, event, key=str(job_id))
    return _to_res(job)


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
    # 발행 이벤트 강화(㊶ C1) — publishing이 mp4 경로·제목·출처를 그대로 쓰도록(출처 계승).
    mp4_path: str = ""
    sources: list[str] = []
    if job.content_id is not None:
        content = await repository.get_content(session, job.content_id)
        if content is not None:
            mp4_path = content.mp4_path
    script = await repository.get_script_by_job(session, job.id)
    if script is not None:
        seen: set[str] = set()
        for c in script.citations:
            url = str(c.get("source_url", ""))
            if url and url not in seen:
                seen.add(url)
                sources.append(url)
    # ㊱ P3 — 직접 publish 대신 **같은 트랜잭션**에 아웃박스 INSERT. Debezium이 발행(유실 0).
    job.status = JobStatus.APPROVED.value
    publish_via_outbox(
        session,
        event_type=settings.topic_approved,
        payload={"job_id": job.id, "content_id": job.content_id, "mp4_path": mp4_path,
                 "title": job.topic, "sources": sources},
        producer="content",
        aggregate_type="content",
        aggregate_id=str(job.id),
        key=str(job.id),
    )
    await session.commit()  # job.status + outbox 원자 커밋
    await session.refresh(job)
    return _to_res(job)


async def search_history(session: AsyncSession, query: str, top_k: int) -> SearchResponse:
    """콘텐츠 히스토리 조회 — 중복회피(키워드/메타). 벡터 아님(ADR 0006)."""
    rows = await repository.history_search(session, query, top_k)
    return SearchResponse(
        hits=[SearchHit(content_id=cid, text=text, score=1.0) for (cid, text) in rows]
    )
