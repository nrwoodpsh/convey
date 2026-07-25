"""admin_db 접근 — 순수 CRUD. 서비스가 조립."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin.models import CollectionSettings, Keyword, SourceToggle, Stock

_SOURCES = ("naver", "rss", "dart")


async def list_stocks(session: AsyncSession) -> list[Stock]:
    rows = (await session.execute(select(Stock).order_by(Stock.ticker))).scalars().all()
    return list(rows)


async def get_stock(session: AsyncSession, ticker: str) -> Stock | None:
    return await session.get(Stock, ticker)


async def list_keywords(session: AsyncSession) -> list[Keyword]:
    rows = (await session.execute(select(Keyword).order_by(Keyword.id))).scalars().all()
    return list(rows)


async def get_keyword(session: AsyncSession, kid: int) -> Keyword | None:
    return await session.get(Keyword, kid)


async def list_sources(session: AsyncSession) -> dict[str, bool]:
    rows = (await session.execute(select(SourceToggle))).scalars().all()
    got = {s.name: s.enabled for s in rows}
    return {name: got.get(name, True) for name in _SOURCES}  # 미설정은 기본 ON


async def get_source(session: AsyncSession, name: str) -> SourceToggle | None:
    return await session.get(SourceToggle, name)


async def get_settings(session: AsyncSession) -> CollectionSettings:
    row = await session.get(CollectionSettings, 1)
    if row is None:
        row = CollectionSettings(id=1, period="1w")
        session.add(row)
        await session.commit()
    return row
