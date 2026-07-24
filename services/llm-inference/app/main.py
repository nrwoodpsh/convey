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
    num_predict: int | None = None  # 출력 토큰 상한(선택). 요약 등 짧은 생성 강제(㉛).
    think: bool | None = None  # 추론 모델 <think> 억제(선택, ㉛).
    keep_alive: str | None = None  # 모델 상주 시간(선택, 예 "30m") — 재적재 방지(㉛).


class ChatReq(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
async def generate(req: GenerateReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    text = await app.state.ollama.generate(
        req.prompt, req.model, req.num_predict, req.think, req.keep_alive
    )
    return {"response": text}


@app.post("/chat")
async def chat(req: ChatReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    text = await app.state.ollama.chat(req.messages, req.model)
    return {"response": text}
