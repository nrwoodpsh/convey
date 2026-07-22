from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.kafka import KafkaProducer
from common.logging import configure_logging
from fastapi import FastAPI

from app.config import settings
from app.consumer import run_assembled_consumer, run_consumer, run_issue_consumer
from app.domains.content.router import router as content_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    app.state.producer = producer
    # API + Kafka 소비 동거: 소비 루프를 백그라운드 태스크로 (갭#5 패턴)
    gen_task = asyncio.create_task(run_consumer(producer))  # content.generate → scripting/assemble
    asm_task = asyncio.create_task(run_assembled_consumer(producer))  # content.assembled → ready
    iss_task = asyncio.create_task(run_issue_consumer(producer))  # issue.selected → 자동 잡 생성
    try:
        yield
    finally:
        gen_task.cancel()
        asm_task.cancel()
        iss_task.cancel()
        await producer.stop()


app = FastAPI(title="content", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(content_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
