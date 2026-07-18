"""item 도메인 서비스 — 트랜잭션 커밋 후 이벤트 발행(간이 아웃박스)."""
from __future__ import annotations

from common.kafka import KafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.item import repository
from app.domains.item.schemas import ItemCreate, ItemOut

EVENT_ITEM_CREATED = "sample.item.created"


async def create_item(
    session: AsyncSession,
    producer: KafkaProducer,
    data: ItemCreate,
    owner_id: str,
    topic: str,
) -> ItemOut:
    item = await repository.create(
        session, name=data.name, description=data.description, owner_id=owner_id
    )
    await session.commit()  # 1) 먼저 커밋
    await producer.publish(  # 2) 커밋 후 발행
        topic,
        {"type": EVENT_ITEM_CREATED, "id": item.id, "name": item.name, "owner_id": owner_id},
        key=str(item.id),
    )
    return ItemOut.model_validate(item)
