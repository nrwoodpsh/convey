from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.errors import register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.logging import configure_logging
from common.security import UserContext
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.agent.loop import AgentLoop
from app.agent.memory import Memory
from app.config import settings
from app.llm_client import LLMClient

configure_logging(settings.log_level)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.llm = LLMClient(settings.llm_inference_url, settings.gateway_internal_secret)
    app.state.agent = AgentLoop(
        llm=app.state.llm,
        memory=Memory(),
        retriever=None,  # RAG 붙일 때 Retriever(Embedder(...), settings.vector_top_k) 주입
        max_steps=settings.max_steps,
    )
    try:
        yield
    finally:
        await app.state.llm.close()


app = FastAPI(title="agent", lifespan=lifespan)
register_exception_handlers(app)


class ChatReq(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatReq, user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    answer = await app.state.agent.run(req.session_id, req.message, user)
    return {"response": answer}
