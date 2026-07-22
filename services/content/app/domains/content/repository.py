"""content 저장소 계층 — 히스토리 조회(중복회피). 벡터 아님(키워드/메타, ADR 0006)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.stocks import stock_name

from app.domains.content.models import Content, GenerationJob, Script
from app.domains.content.schemas import JobListItem


async def history_search(
    session: AsyncSession, query: str, top_k: int
) -> list[tuple[int, str]]:
    """완성 콘텐츠를 주제 키워드로 조회 → (content_id, topic). 최신순. 중복회피·이력 조회용.

    Content(완성본)가 있는 잡만. topic ILIKE(벡터 아님). 무매칭이면 빈 목록.
    """
    like = f"%{query}%"
    stmt = (
        select(Content.id, GenerationJob.topic)
        .join(GenerationJob, Content.job_id == GenerationJob.id)
        .where(GenerationJob.topic.ilike(like))
        .order_by(Content.created_at.desc())
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]


async def recent_ticker_job(
    session: AsyncSession, ticker: str, *, window_days: int
) -> bool:
    """같은 종목의 최근(window) 잡이 있고 실패가 아니면 True — 자동 양산 중복회피 판정.

    진행 중(scripting/assembling)·완료(ready/approved)도 중복으로 봄(재기동 재발행 억제).
    실패(failed)는 재시도 허용이라 제외.
    """
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    stmt = (
        select(func.count())
        .select_from(GenerationJob)
        .where(
            GenerationJob.ticker == ticker,
            GenerationJob.status != "failed",
            GenerationJob.created_at >= since,
        )
    )
    count = (await session.execute(stmt)).scalar_one()
    return int(count) > 0


async def list_jobs(session: AsyncSession, *, limit: int = 50) -> list[JobListItem]:
    """최근 잡 목록 — 최신순(created_at desc). 대시보드 이력(ADR 0010)."""
    stmt = select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(limit)
    jobs = (await session.execute(stmt)).scalars().all()
    return [
        JobListItem(
            job_id=j.id,
            topic=j.topic,
            ticker=j.ticker,
            name=stock_name(j.ticker),  # 한글명(공유 사전) — 대시보드는 코드 대신 이름 표시
            status=j.status,
            content_id=j.content_id,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


async def get_content(session: AsyncSession, content_id: int) -> Content | None:
    """완성본(Content) 조회 — mp4 스트리밍 경로 확인용. 없으면 None."""
    return await session.get(Content, content_id)


async def get_script_by_job(session: AsyncSession, job_id: int) -> Script | None:
    """잡의 스크립트(시나리오) 조회 — 미리보기용. 최신 1건. 없으면 None."""
    stmt = (
        select(Script)
        .where(Script.job_id == job_id)
        .order_by(Script.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()
