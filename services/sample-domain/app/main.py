from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.kafka import KafkaProducer
from common.logging import configure_logging
from fastapi import FastAPI

from app.config import settings
from app.domains.item.router import router as item_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    app.state.producer = producer
    try:
        yield
    finally:
        await producer.stop()


app = FastAPI(title="sample-domain", lifespan=lifespan)
register_exception_handlers(app)

# 도메인 라우터 조립 (기능별 패키지) — 새 도메인은 여기에 include_router 추가
app.include_router(item_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
