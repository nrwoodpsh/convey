"""운영 대시보드 라우터 — 로컬 전용·무인증(ADR 0010·0011). 라운드㉒·㉓.

CONVEY 첫 브라우저 화면. content 호스트 포트(8091)로 직접 접속. 워크플로우(㉓):
  오늘자 기사 목록 → 선택 → 진행(초안) → 시나리오 제시 → 승인 → 쇼츠 생성.

  GET  /                              정적 대시보드(index.html)
  GET  /ui/articles                   오늘자 수집 기사(research east-west)
  POST /ui/generate                   기사 선택 → 초안 잡(스크립트만, 승인 대기)
  GET  /ui/jobs                       잡 목록(최신순)
  GET  /ui/jobs/{id}                  상태 폴링(JobRes)
  GET  /ui/jobs/{id}/script           시나리오 제시(승인 전)
  POST /ui/jobs/{id}/approve-scenario 승인 → media.assemble → 합성 시작
  GET  /ui/contents/{id}/script       완성본 시나리오
  GET  /ui/contents/{id}/video        완성 mp4 스트리밍(Range)

주의: 이 라우터는 gateway_user(HMAC) 의존성을 붙이지 않는다(무인증).
기존 /content/* (gateway·HMAC 보호)는 불변. 발행은 여전히 사람 승인.
"""
from __future__ import annotations

import os
from pathlib import Path

from common.errors import AppError
from common.kafka import KafkaProducer
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import research_client
from app.db import get_session
from app.domains.content import repository, service
from app.domains.content.models import Script
from app.domains.content.schemas import (
    ApproveScenarioReq,
    ArticleItem,
    ArticleListRes,
    DashboardGenerateReq,
    GenerateRequest,
    JobListRes,
    JobRes,
    ScriptCiteView,
    ScriptEditReq,
    ScriptSectionView,
    ScriptView,
)

router = APIRouter(tags=["dashboard"])

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.producer  # type: ignore[no-any-return]


def _to_script_view(script: Script | None) -> ScriptView:
    """Script → ScriptView(시나리오). 수치 슬롯은 사실값으로 채움. 없으면 빈 뷰."""
    if script is None:
        return ScriptView()
    sections: list[ScriptSectionView] = []
    for sec in script.sections:
        text = str(sec.get("text", ""))
        slots = sec.get("data_slots") or {}
        if slots:
            try:
                text = text.format(**slots)  # "{close}"→사실값(환각 아님)
            except (KeyError, IndexError, ValueError):
                pass
        if text.strip():
            sections.append(ScriptSectionView(kind=str(sec.get("kind", "")), text=text.strip()))
    citations = [
        ScriptCiteView(claim=str(c.get("claim", "")), source_url=str(c.get("source_url", "")))
        for c in script.citations
        if c.get("source_url")
    ]
    return ScriptView(sections=sections, citations=citations)


@router.get("/")
async def dashboard() -> FileResponse:
    """정적 대시보드 셸. 캐시 금지(재빌드 시 브라우저가 옛 FE를 붙잡지 않게)."""
    return FileResponse(
        _INDEX_HTML,
        media_type="text/html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@router.get("/ui/articles", response_model=ArticleListRes)
async def ui_articles(limit: int = 50) -> ArticleListRes:
    """오늘자 수집 기사(research east-west) — 항상 당일만(㉔, 폴백 없음)."""
    rows = await research_client.fetch_articles(window_days=1, limit=limit)
    items = [
        ArticleItem(
            article_id=int(r["article_id"]),
            title=str(r.get("title", "")),
            source_url=str(r.get("source_url", "")),
            published_at=str(r.get("published_at", "")),
            ticker=r.get("ticker"),
            name=r.get("name"),
        )
        for r in rows
    ]
    return ArticleListRes(items=items)


@router.post("/ui/generate", status_code=202)
async def ui_generate(
    payload: DashboardGenerateReq,
    session: AsyncSession = Depends(get_session),
    producer: KafkaProducer = Depends(get_producer),
) -> dict[str, int]:
    """기사+템플릿 선택 → 초안 잡(스크립트만, 승인 대기). auto=False로 시나리오 승인 게이트 진입."""
    ref = str(payload.article_id) if payload.article_id is not None else None
    req = GenerateRequest(topic=payload.title, ticker=payload.ticker, issue_ref=ref)
    job_id = await service.start_generation(
        session, producer, req, owner_id="dashboard", auto=False, template=payload.template
    )
    return {"job_id": job_id}


@router.get("/ui/jobs", response_model=JobListRes)
async def ui_jobs(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> JobListRes:
    """최근 잡 목록 — 최신순."""
    items = await repository.list_jobs(session, limit=max(1, min(limit, 200)))
    return JobListRes(items=items)


@router.get("/ui/jobs/{job_id}", response_model=JobRes)
async def ui_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> JobRes:
    """상태 폴링 — 기존 get_job 재사용."""
    return await service.get_job(session, job_id)


@router.get("/ui/jobs/{job_id}/script", response_model=ScriptView)
async def ui_job_script(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> ScriptView:
    """시나리오 제시(승인 전) — 잡의 Script. 종목코드 없이 한글명(agent 생성)."""
    script = await repository.get_script_by_job(session, job_id)
    return _to_script_view(script)


@router.put("/ui/jobs/{job_id}/script", response_model=JobRes)
async def ui_edit_script(
    job_id: int,
    payload: ScriptEditReq,
    session: AsyncSession = Depends(get_session),
) -> JobRes:
    """시나리오 수정 저장(㉔) — 편집한 섹션 텍스트로 갱신. scenario_ready만(아니면 CNT003)."""
    sections = [{"kind": s.kind, "text": s.text} for s in payload.sections]
    return await service.update_script(session, job_id, sections)


@router.post("/ui/jobs/{job_id}/approve-scenario", response_model=JobRes)
async def ui_approve_scenario(
    job_id: int,
    payload: ApproveScenarioReq | None = None,
    session: AsyncSession = Depends(get_session),
    producer: KafkaProducer = Depends(get_producer),
) -> JobRes:
    """시나리오 승인+배경(㉓·㉔) → media.assemble 발행 → 합성 시작. scenario_ready만 통과."""
    background = payload.background if payload is not None else "real"
    return await service.approve_scenario(session, producer, job_id, background=background)


@router.get("/ui/contents/{content_id}/script", response_model=ScriptView)
async def ui_script(
    content_id: int,
    session: AsyncSession = Depends(get_session),
) -> ScriptView:
    """완성본 시나리오 — content_id → job → Script."""
    content = await repository.get_content(session, content_id)
    if content is None:
        raise AppError("CNT004", "완성본(mp4)을 찾을 수 없습니다.", status=404)
    script = await repository.get_script_by_job(session, content.job_id)
    return _to_script_view(script)


@router.get("/ui/contents/{content_id}/video")
async def ui_video(
    content_id: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """완성 mp4 스트리밍 — content_id로 경로 확인 후 서빙(경로 주입 방지). Range 자동."""
    content = await repository.get_content(session, content_id)
    if content is None or not os.path.exists(content.mp4_path):
        raise AppError("CNT004", "완성본(mp4)을 찾을 수 없습니다.", status=404)
    return FileResponse(
        content.mp4_path,
        media_type="video/mp4",
        filename=f"convey-{content_id}.mp4",
    )
