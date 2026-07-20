"""publishing 서비스 — 멱등 발행 상태머신. 라운드⑤ (알파4: 양산 신뢰성).

queued→uploading→published/failed. content_id 유니크로 **중복 업로드 방지**(멱등).
실패는 재시도 가능(상태 기반). 발행은 사람 승인(content.approved) 후에만.
"""
from __future__ import annotations

from common.errors import AppError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PublishRecord
from app.schemas import PublishRes, PublishStatus


def _to_res(rec: PublishRecord) -> PublishRes:
    return PublishRes(
        content_id=rec.content_id, channel=rec.channel, status=rec.status,
        external_url=rec.external_url, error=rec.error,
    )


async def _get(session: AsyncSession, content_id: int) -> PublishRecord | None:
    result = await session.execute(
        select(PublishRecord).where(PublishRecord.content_id == content_id)
    )
    return result.scalar_one_or_none()


async def enqueue(session: AsyncSession, content_id: int, channel: str = "youtube") -> PublishRes:
    """발행 큐잉 — 멱등. 이미 기록이 있으면 그대로 반환(중복 업로드 방지)."""
    existing = await _get(session, content_id)
    if existing is not None:
        return _to_res(existing)
    rec = PublishRecord(content_id=content_id, channel=channel, status=PublishStatus.QUEUED.value)
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return _to_res(rec)


async def mark_published(session: AsyncSession, content_id: int, external_url: str) -> PublishRes:
    rec = await _get(session, content_id)
    if rec is None:
        raise AppError("PUB003", "발행 기록 없음", status=404)
    rec.status = PublishStatus.PUBLISHED.value
    rec.external_url = external_url
    rec.error = None
    await session.commit()
    await session.refresh(rec)
    return _to_res(rec)


async def mark_failed(session: AsyncSession, content_id: int, error: str) -> PublishRes:
    rec = await _get(session, content_id)
    if rec is None:
        raise AppError("PUB003", "발행 기록 없음", status=404)
    rec.status = PublishStatus.FAILED.value
    rec.error = error
    await session.commit()
    await session.refresh(rec)
    return _to_res(rec)


async def get_status(session: AsyncSession, content_id: int) -> PublishRes:
    rec = await _get(session, content_id)
    if rec is None:
        raise AppError("PUB003", "발행 기록 없음", status=404)
    return _to_res(rec)
