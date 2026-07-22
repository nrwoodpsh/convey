"""content Kafka 소비 — 근거 기반 쇼츠 오케스트레이션. 라운드⑤ (키 없는 경로).

content는 잡 상태머신을 소유하고, 두 흐름을 소비한다:
  1) content.generate → scripting(agent 호출) → Script 저장 → media.assemble 발행
  2) content.assembled(video-assembly 완료 fan-in) → Content 저장 → status=ready(사람 승인 대기)
가드레일: 수치·인용은 agent가 사실에 결속(환각0). 발행은 사람 승인 후(별도).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.kafka import KafkaProducer, consume_forever
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.config import settings
from app.db import SessionLocal
from app.domains.content import repository, service
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


async def _call_agent_script(job_id: int, topic: str, ticker: str | None) -> dict[str, Any]:
    """agent /agent/script east-west 호출(HMAC 서명)."""
    path = "/agent/script"
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="content", path=path)
    headers = {H_USER_ID: "content", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{settings.agent_url.rstrip('/')}{path}",
            json={"job_id": job_id, "topic": topic, "ticker": ticker},
            headers=headers,
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result


# broll 배경 검색어 — Pexels 커버리지상 영문 금융 키워드가 안정적(POC).
# 섹터→영문 매핑은 후속(라운드⑫ History).
_BROLL_QUERY = "stock market"


def _narration(sections: list[dict[str, Any]]) -> str:
    """스크립트 섹션 → 내레이션 문장(로컬 TTS가 읽음). chart 슬롯({close} 등)은 사실값으로 해소.

    수치는 이미 사실 슬롯(환각 무관) — 그대로 읽어도 안전.
    """
    parts: list[str] = []
    for sec in sections:
        text = str(sec.get("text", ""))
        slots = sec.get("data_slots") or {}
        if sec.get("kind") == "chart" and slots:
            try:
                text = text.format(**slots)  # "{close}"→실제 종가 등
            except (KeyError, IndexError, ValueError):
                pass
        if text.strip():
            parts.append(text.strip())
    return " ".join(parts)


async def handle_generate(event: dict[str, Any], producer: KafkaProducer) -> None:
    """content.generate → scripting → Script 저장 → media.assemble 발행."""
    job_id = int(event["job_id"])
    topic = str(event["topic"])
    ticker = event.get("ticker")
    await _set_status(job_id, JobStatus.SCRIPTING)

    try:
        script_res = await _call_agent_script(job_id, topic, ticker)
    except Exception as exc:  # noqa: BLE001 — 실패는 잡에 기록하고 계속(워커 생존)
        await _set_status(job_id, JobStatus.FAILED, error=f"script: {exc}"[:500])
        logger.exception("스크립트 생성 실패 job=%s", job_id)
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
    hook = next((s["text"] for s in sections if s.get("kind") == "hook"), topic)
    narration = _narration(sections)
    await _set_status(job_id, JobStatus.ASSEMBLING, script_id=script_id)
    await producer.publish(
        settings.topic_assemble,
        {
            "job_id": job_id, "chart": chart, "title": topic,
            "subtitle": hook, "narration": narration,
            "broll_query": _BROLL_QUERY, "duration": 6.0,
        },
        key=str(job_id),
    )
    logger.info("media.assemble 발행 job=%s script=%s", job_id, script_id)


async def handle_assembled(event: dict[str, Any], producer: KafkaProducer) -> None:
    """content.assembled(video-assembly 완료) → Content 저장 → status=ready."""
    job_id = int(event["job_id"])
    ok = bool(event.get("ok"))
    mp4_path = event.get("mp4_path")
    if not ok or not mp4_path:
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
    name = str(event.get("name") or ticker)
    async with SessionLocal() as session:
        # 중복회피(A2): 같은 종목 최근 잡 있으면 skip (자동 양산 스팸 방지)
        if await repository.recent_ticker_job(
            session, ticker, window_days=settings.dedup_window_days
        ):
            logger.info("중복회피: ticker=%s 최근 잡 존재 → 자동 생성 skip", ticker)
            return
        req = GenerateRequest(topic=f"{name} 이슈", ticker=ticker)
        job_id = await service.start_generation(session, producer, req, owner_id="auto")
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
