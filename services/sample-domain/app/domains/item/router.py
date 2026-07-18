from __future__ import annotations

from common.errors import AppError
from common.gateway_auth import make_gateway_dep
from common.kafka import KafkaProducer
from common.security import UserContext
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.domains.item import repository, service
from app.domains.item.schemas import ItemCreate, ItemOut

router = APIRouter(prefix="/items", tags=["item"])
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.producer  # type: ignore[no-any-return]


@router.post("", response_model=ItemOut, status_code=201)
async def create_item(
    payload: ItemCreate,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
    producer: KafkaProducer = Depends(get_producer),
) -> ItemOut:
    return await service.create_item(
        session, producer, payload, user.user_id, settings.topic_events
    )


@router.get("", response_model=list[ItemOut])
async def list_items(
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> list[ItemOut]:
    return [ItemOut.model_validate(i) for i in await repository.list_all(session)]


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(
    item_id: int,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> ItemOut:
    item = await repository.get(session, item_id)
    if item is None:
        raise AppError("not_found", "아이템 없음", status=404)
    return ItemOut.model_validate(item)
