"""publishing — 발행 상태 조회 API + content.approved 소비(업로드). 라운드⑤."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.logging import configure_logging
from common.security import UserContext
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.config import settings
from app.consumer import run_consumer
from app.db import get_session
from app.schemas import PublishRes

configure_logging(settings.log_level)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(run_consumer())  # content.approved 백그라운드 소비
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="publishing", lifespan=lifespan)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/publishing/{content_id}", response_model=PublishRes)
async def publish_status(
    content_id: int,
    user: UserContext = Depends(gateway_user),
    session: AsyncSession = Depends(get_session),
) -> PublishRes:
    return await service.get_status(session, content_id)
