from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.kafka import KafkaProducer
from common.logging import configure_logging
from fastapi import FastAPI
from neo4j import GraphDatabase

from app.config import settings
from app.domains.research.router import router as research_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    app.state.producer = producer
    user, _, pw = settings.neo4j_auth.partition("/")
    app.state.neo4j = GraphDatabase.driver(settings.neo4j_url, auth=(user, pw))
    try:
        yield
    finally:
        await producer.stop()
        app.state.neo4j.close()


app = FastAPI(title="research", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(research_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
