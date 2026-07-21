"""research 저장소 계층(Postgres 사실) — Article·PriceTick 조회.

관계·인과 그래프(Neo4j)는 GraphRepo(app/graph)에서 다룬다.
가드레일: Article.source_url은 NOT NULL이라 회수 결과는 항상 출처를 동반(무출처 0).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.research.models import Article, PriceTick


async def upsert_price_tick(
    session: AsyncSession,
    *,
    ticker: str,
    ts: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int,
) -> tuple[int, bool]:
    """market.ticks → PriceTick 멱등 저장. 반환 (id, created).

    market-feed가 같은 일봉을 반복 발행하므로 (ticker, ts) 동일하면 OHLCV만 갱신(장중 값
    수렴), 없으면 삽입. 가드레일: 값 조작 없이 이벤트 실측 그대로 저장.
    """
    existing = (
        await session.execute(
            select(PriceTick).where(PriceTick.ticker == ticker, PriceTick.ts == ts)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.open = open_
        existing.high = high
        existing.low = low
        existing.close = close
        existing.volume = volume
        await session.commit()
        return existing.id, False
    tick = PriceTick(
        ticker=ticker, ts=ts, open=open_, high=high, low=low, close=close, volume=volume
    )
    session.add(tick)
    await session.commit()
    await session.refresh(tick)
    return tick.id, True


async def fact_search(
    session: AsyncSession, query: str, top_k: int, *, window_days: int | None = None
) -> list[tuple[int, str, str]]:
    """키워드로 Article 회수(제목·본문 ILIKE). window_days 있으면 기간 필터. 반환 (id, title, source_url)."""
    like = f"%{query}%"
    stmt = select(Article.id, Article.title, Article.source_url).where(
        or_(Article.title.ilike(like), Article.body.ilike(like))
    )
    if window_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        stmt = stmt.where(Article.published_at >= since)
    stmt = stmt.order_by(Article.published_at.desc()).limit(top_k)
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]


async def source_urls_for(session: AsyncSession, ids: list[int]) -> dict[int, str]:
    """기사 id → source_url. 그래프 관계의 근거 기사 URL 해석에 사용."""
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(Article.id, Article.source_url).where(Article.id.in_(ids))
        )
    ).all()
    return {row[0]: row[1] for row in rows}
