from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx
from common.errors import AppError, register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.logging import configure_logging
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, UserContext, sign_internal
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from app.agent.loop import AgentLoop
from app.agent.memory import Memory
from app.config import settings
from app.llm_client import LLMClient
from app.rag.retriever import Retriever
from app.script.builder import build_script

configure_logging(settings.log_level)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)


def _sync_llm(secret: str, base_url: str) -> Callable[[str], str]:
    """build_script용 동기 LLM 호출자 — llm-inference /generate(로컬 Ollama), HMAC 서명."""

    def call(prompt: str) -> str:
        path = "/generate"
        ts, sig = sign_internal(secret=secret, user_id="agent", path=path)
        resp = httpx.post(
            f"{base_url.rstrip('/')}{path}",
            json={"prompt": prompt},
            headers={H_USER_ID: "agent", H_TIMESTAMP: ts, H_SIGNATURE: sig},
            timeout=240,
        )
        resp.raise_for_status()
        return str(resp.json().get("response", ""))

    return call


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.llm = LLMClient(settings.llm_inference_url, settings.gateway_internal_secret)
    app.state.agent = AgentLoop(
        llm=app.state.llm,
        memory=Memory(),
        retriever=None,  # /chat 루프는 근거회수 미사용(스크립트 경로는 아래 Retriever)
        max_steps=settings.max_steps,
    )
    app.state.retriever = Retriever(
        settings.research_url, settings.content_url,
        settings.retrieval_top_k, settings.gateway_internal_secret,
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


# ── 근거 스크립트 생성 (content → agent, east-west) — 라운드⑤ ──
class ScriptReq(BaseModel):
    job_id: int
    topic: str = Field(min_length=1, max_length=200)
    ticker: str | None = None


class CitationOut(BaseModel):
    claim: str
    source_url: str
    ref_id: int


class SectionOut(BaseModel):
    kind: str
    text: str
    data_slots: dict[str, str] = Field(default_factory=dict)


class ChartOut(BaseModel):
    ticker: str
    close: float
    change_pct: float
    series: list[float] = Field(default_factory=list)


class ScriptRes(BaseModel):
    sections: list[SectionOut] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    chart: ChartOut | None = None


@app.post("/agent/script", response_model=ScriptRes)
async def agent_script(req: ScriptReq, user: UserContext = Depends(gateway_user)) -> ScriptRes:
    """근거 스크립트 생성 — research /search로 근거 회수 → 템플릿+사실슬롯(수치=사실만)."""
    ev = await app.state.retriever.gather(req.topic, ticker=req.ticker, entity=req.ticker)
    if ev.price is None:
        raise AppError("AGENT001", "가격 근거가 없어 스크립트를 만들 수 없습니다.", status=422)
    llm = _sync_llm(settings.gateway_internal_secret, settings.llm_inference_url)
    # build_script + 그 안의 동기 LLM 호출을 스레드로 격리(이벤트루프 비블로킹)
    script = await asyncio.to_thread(build_script, req.topic, ev.price, ev.facts, llm, ev.macros)
    chart = ChartOut(
        ticker=ev.price["ticker"], close=ev.price["close"],
        change_pct=ev.price["change_pct"], series=ev.series,
    )
    return ScriptRes(
        sections=[
            SectionOut(kind=s.kind, text=s.text, data_slots=s.data_slots) for s in script.sections
        ],
        citations=[
            CitationOut(claim=c.claim, source_url=c.source_url, ref_id=c.ref_id)
            for c in script.citations
        ],
        chart=chart,
    )
