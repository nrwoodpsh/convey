from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.item.models import Item


async def create(
    session: AsyncSession, *, name: str, description: str | None, owner_id: str
) -> Item:
    item = Item(name=name, description=description, owner_id=owner_id)
    session.add(item)
    await session.flush()  # id 채우기
    return item


async def get(session: AsyncSession, item_id: int) -> Item | None:
    return await session.get(Item, item_id)


async def list_all(session: AsyncSession, *, limit: int = 100) -> list[Item]:
    rows = await session.execute(select(Item).order_by(Item.id.desc()).limit(limit))
    return list(rows.scalars().all())
