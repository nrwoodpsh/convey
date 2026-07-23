"""content Kafka 소비 — 근거 기반 쇼츠 오케스트레이션. 라운드⑤ (키 없는 경로).

content는 잡 상태머신을 소유하고, 두 흐름을 소비한다:
  1) content.generate → scripting(agent 호출) → Script 저장 → media.assemble 발행
  2) content.assembled(video-assembly 완료 fan-in) → Content 저장 → status=ready(사람 승인 대기)
가드레일: 수치·인용은 agent가 사실에 결속(환각0). 발행은 사람 승인 후(별도).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from common.kafka import KafkaProducer, consume_forever
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from common.stocks import stock_name

from app.config import settings
from app.db import SessionLocal
from app.domains.content import media, repository, service
from app.domains.content.models import Content, GenerationJob, Script
from app.domains.content.schemas import GenerateRequest, JobStatus

logger = logging.getLogger("content.consumer")


async def _set_status(job_id: int, status: JobStatus, **fields: Any) -> None:
    """잡 상태 전이(+선택 필드). 잡 없으면 무시(로그)."""
    async with SessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if job is None:
            logger.warning("잡 없음 job=%s", job_id)
            return
        job.status = status.value
        for key, value in fields.items():
            setattr(job, key, value)
        await session.commit()


async def _call_agent_script(
    job_id: int, topic: str, ticker: str | None, template: str = "analysis"
) -> dict[str, Any]:
    """agent /agent/script east-west 호출(HMAC 서명). template(㉔): 시나리오 구성·톤."""
    path = "/agent/script"
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="content", path=path)
    headers = {H_USER_ID: "content", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{settings.agent_url.rstrip('/')}{path}",
            json={"job_id": job_id, "topic": topic, "ticker": ticker, "template": template},
            headers=headers,
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result


async def handle_generate(event: dict[str, Any], producer: KafkaProducer) -> None:
    """content.generate → scripting → Script 저장.

    auto=True(자동양산): 곧바로 media.assemble 발행(assembling). auto=False(대시보드 수동, ㉓):
    chart 근거를 잡에 보존하고 scenario_ready에서 정지(사람 승인 대기). 승인은 approve_scenario.
    """
    job_id = int(event["job_id"])
    topic = str(event["topic"])
    ticker = event.get("ticker")
    auto = bool(event.get("auto", True))  # 값 없으면 안전값(기존 자동 경로)
    template = str(event.get("template", "analysis"))  # 시나리오 템플릿(㉔)
    await _set_status(job_id, JobStatus.SCRIPTING)

    # 스크립트 생성 — 일시 실패(LLM 타임아웃 등) 재시도(㉙/F1, 상한·백오프).
    script_res = None
    last_exc: Exception | None = None
    for attempt in range(settings.retry_max + 1):
        try:
            script_res = await _call_agent_script(job_id, topic, ticker, template)
            break
        except Exception as exc:  # noqa: BLE001 — 재시도 후 최종 실패만 기록
            last_exc = exc
            logger.warning("스크립트 생성 실패(시도 %s) job=%s: %s", attempt + 1, job_id, exc)
            if attempt < settings.retry_max:
                await asyncio.sleep(settings.retry_backoff_sec)
    if script_res is None:
        await _set_status(job_id, JobStatus.FAILED, error=f"script: {last_exc}"[:500])
        logger.exception("스크립트 생성 최종 실패 job=%s", job_id, exc_info=last_exc)
        return

    # Script 저장
    async with SessionLocal() as session:
        script = Script(
            job_id=job_id,
            sections=script_res.get("sections", []),
            citations=script_res.get("citations", []),
        )
        session.add(script)
        await session.commit()
        await session.refresh(script)
        script_id = script.id

    chart = script_res.get("chart")
    if not chart:
        await _set_status(job_id, JobStatus.FAILED, script_id=script_id, error="차트 근거 없음")
        return

    sections = script_res.get("sections", [])
    if not auto:
        # 수동(대시보드): 시나리오 승인 대기 — chart 보존, 합성 발행 안 함
        await _set_status(job_id, JobStatus.SCENARIO_READY, script_id=script_id, chart=chart)
        logger.info("시나리오 준비(승인 대기) job=%s script=%s", job_id, script_id)
        return

    # 자동(양산): 곧바로 합성
    await _set_status(job_id, JobStatus.ASSEMBLING, script_id=script_id, chart=chart)
    event_out = media.build_assemble_event(
        job_id=job_id, topic=topic, ticker=ticker, chart=chart,
        sections=sections, narration_max_chars=settings.narration_max_chars,
        citations=script_res.get("citations", []),
        date=datetime.now(timezone.utc).date().isoformat(),
    )
    await producer.publish(settings.topic_assemble, event_out, key=str(job_id))
    logger.info("media.assemble 발행 job=%s script=%s", job_id, script_id)


async def _retry_assemble(job_id: int, producer: KafkaProducer, err: str) -> bool:
    """합성 일시 실패 재시도(㉙/F1) — 상한 내면 chart+script로 media.assemble 재발행. 재발행하면 True."""
    async with SessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if job is None or not job.chart or job.retry_count >= settings.retry_max:
            return False
        job.retry_count += 1
        job.status = JobStatus.ASSEMBLING.value
        await session.commit()
        script = await repository.get_script_by_job(session, job_id)
        sections = script.sections if script is not None else []
        citations = script.citations if script is not None else []
        n = job.retry_count
        event_out = media.build_assemble_event(
            job_id=job_id, topic=job.topic, ticker=job.ticker, chart=job.chart,
            sections=sections, narration_max_chars=settings.narration_max_chars,
            citations=citations, date=job.created_at.date().isoformat(),
        )
    await asyncio.sleep(settings.retry_backoff_sec)
    await producer.publish(settings.topic_assemble, event_out, key=str(job_id))
    logger.info("합성 재시도 %s/%s job=%s (이전 오류: %s)", n, settings.retry_max, job_id, err[:100])
    return True


async def handle_assembled(event: dict[str, Any], producer: KafkaProducer) -> None:
    """content.assembled(video-assembly 완료) → Content 저장 → status=ready."""
    job_id = int(event["job_id"])
    ok = bool(event.get("ok"))
    mp4_path = event.get("mp4_path")
    if not ok or not mp4_path:
        # 합성 일시 실패 — 상한 내 재시도(㉙/F1, 멱등: 같은 job으로 media.assemble 재발행)
        if await _retry_assemble(job_id, producer, str(event.get("error") or "")):
            return
        await _set_status(job_id, JobStatus.FAILED, error=(str(event.get("error") or "합성 실패"))[:500])
        logger.warning("합성 실패 job=%s: %s", job_id, event.get("error"))
        return

    async with SessionLocal() as session:
        content = Content(
            job_id=job_id,
            mp4_path=str(mp4_path),
            broll_source_url=event.get("broll_source_url"),  # 가드레일: 자산 출처 계승
            broll_author=event.get("broll_author"),
            broll_license=event.get("broll_license"),
        )
        session.add(content)
        await session.commit()
        await session.refresh(content)
        job = await session.get(GenerationJob, job_id)
        if job is not None:
            job.status = JobStatus.READY.value  # 내부 상태 — 사람 승인 대기
            job.content_id = content.id
            await session.commit()
        content_id = content.id

    await producer.publish(
        settings.topic_ready, {"job_id": job_id, "content_id": content_id}, key=str(job_id)
    )
    logger.info("쇼츠 ready job=%s content=%s mp4=%s", job_id, content_id, mp4_path)


async def handle_issue(event: dict[str, Any], producer: KafkaProducer) -> None:
    """issue.selected(자동 양산, 알파4) → start_generation으로 자동 잡 생성. 수동 POST와 동일 경로.

    발행은 여전히 사람 승인(불변) — 자동은 ready까지만.
    """
    ticker = str(event.get("ticker", ""))
    if not ticker:
        return
    # 제목이 코드로 나오지 않게 한글명 우선(이벤트 name → 공유 사전 → 최후 코드)
    name = str(event.get("name") or stock_name(ticker) or ticker)
    async with SessionLocal() as session:
        # 중복회피(A2): 같은 종목 최근 잡 있으면 skip (자동 양산 스팸 방지)
        if await repository.recent_ticker_job(
            session, ticker, window_days=settings.dedup_window_days
        ):
            logger.info("중복회피: ticker=%s 최근 잡 존재 → 자동 생성 skip", ticker)
            return
        req = GenerateRequest(topic=f"{name} 이슈", ticker=ticker)
        # 자동양산(알파4)은 승인 게이트 없이 ready까지 무정지(auto=True)
        job_id = await service.start_generation(session, producer, req, owner_id="auto", auto=True)
    logger.info("자동 양산 잡 생성 job=%s ticker=%s", job_id, ticker)


async def run_consumer(producer: KafkaProducer) -> None:
    """lifespan 백그라운드 — content.generate 소비."""

    async def handler(event: dict[str, Any]) -> None:
        await handle_generate(event, producer)

    await consume_forever(
        topic=settings.topic_generate,
        group_id=f"{settings.consumer_group}-generate",
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )


async def run_assembled_consumer(producer: KafkaProducer) -> None:
    """lifespan 백그라운드 — content.assembled(fan-in) 소비."""

    async def handler(event: dict[str, Any]) -> None:
        await handle_assembled(event, producer)

    await consume_forever(
        topic=settings.topic_assembled,
        group_id=f"{settings.consumer_group}-assembled",
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )


async def run_issue_consumer(producer: KafkaProducer) -> None:
    """lifespan 백그라운드 — issue.selected(자동 양산) 소비 → 자동 잡 생성."""

    async def handler(event: dict[str, Any]) -> None:
        await handle_issue(event, producer)

    await consume_forever(
        topic=settings.topic_issue_selected,
        group_id=f"{settings.consumer_group}-issue",
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )
