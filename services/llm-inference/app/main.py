from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.gateway_auth import make_gateway_dep
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
    try:
        yield
    finally:
        await app.state.ollama.close()


app = FastAPI(title="llm-inference", lifespan=lifespan)
register_exception_handlers(app)


class GenerateReq(BaseModel):
    prompt: str
    model: str | None = None


class ChatReq(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None


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
