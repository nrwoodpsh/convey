from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.kafka import KafkaProducer
from common.logging import configure_logging
from common.security import UserContext
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.config import settings
from app.ollama_client import OllamaClient

configure_logging(settings.log_level)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
    app.state.producer = KafkaProducer(settings.kafka_bootstrap)
    await app.state.producer.start()
    try:
        yield
    finally:
        await app.state.ollama.close()
        await app.state.producer.stop()


app = FastAPI(title="llm-inference", lifespan=lifespan)
register_exception_handlers(app)


class GenerateReq(BaseModel):
    prompt: str
    model: str | None = None


class ChatReq(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None


class TrainReq(BaseModel):
    base_model: str
    dataset_ref: str
    epochs: int = 1


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
async def generate(req: GenerateReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    text = await app.state.ollama.generate(req.prompt, req.model)
    return {"response": text}


@app.post("/chat")
async def chat(req: ChatReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    text = await app.state.ollama.chat(req.messages, req.model)
    return {"response": text}


@app.post("/train", status_code=202)
async def submit_train(req: TrainReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    """LoRA 학습잡을 Kafka로 발행 → llm-trainer 워커가 소비."""
    job = {
        "type": "lora.train.requested",
        "base_model": req.base_model,
        "dataset_ref": req.dataset_ref,
        "epochs": req.epochs,
        "requested_by": user.user_id,
    }
    await app.state.producer.publish(settings.topic_train_jobs, job, key=user.user_id)
    return {"status": "queued"}
