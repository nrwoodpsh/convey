from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.kafka import KafkaProducer
from common.logging import configure_logging
from fastapi import FastAPI
from neo4j import GraphDatabase

from app.config import settings
from app.consumer import run_consumer, run_tick_consumer
from app.domains.research.router import router as research_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    app.state.producer = producer
    user, _, pw = settings.neo4j_auth.partition("/")
    app.state.neo4j = GraphDatabase.driver(settings.neo4j_url, auth=(user, pw))
    consumer_task = asyncio.create_task(run_consumer())  # research.ingested 백그라운드 소비
    tick_task = asyncio.create_task(run_tick_consumer())  # market.ticks → PriceTick 백그라운드 소비
    try:
        yield
    finally:
        consumer_task.cancel()
        tick_task.cancel()
        await producer.stop()
        app.state.neo4j.close()


app = FastAPI(title="research", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(research_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
