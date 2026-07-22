"""issue-detector — 워커(스트림 집계) + 얇은 조회 API. 알파2. 라운드②.

GET /issues/today: 현재 윈도우의 이슈 종목 랭킹(조회 상태 — 이벤트 아님). 사람이 보고 선택.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from common.errors import register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.logging import configure_logging
from common.security import UserContext
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.config import settings
from app.ranking import RankWeights, RollingRanker
from app.worker import run_consumers, run_emitter

configure_logging(settings.log_level)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)
ranker = RollingRanker(RankWeights(settings.w_change, settings.w_volume, settings.w_news))


class IssueRankItem(BaseModel):
    ticker: str
    name: str = ""
    score: float
    price_change_pct: float
    volume_z: float
    news_count: int
    rank: int


class IssuesTodayRes(BaseModel):
    as_of: datetime
    window_hours: int
    items: list[IssueRankItem]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(run_consumers(ranker))  # market.ticks·research.ingested 백그라운드 소비
    emit_task = asyncio.create_task(run_emitter(ranker))  # 상위 이슈 → issue.selected(자동 양산)
    try:
        yield
    finally:
        task.cancel()
        emit_task.cancel()


app = FastAPI(title="issue-detector", lifespan=lifespan)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/issues/today", response_model=IssuesTodayRes)
async def issues_today(
    top_k: int = 10,
    window_hours: int | None = None,
    user: UserContext = Depends(gateway_user),
) -> IssuesTodayRes:
    wh = window_hours or settings.window_hours
    now = datetime.now(timezone.utc)
    ranked = ranker.top(top_k, wh, now)
    items = [
        IssueRankItem(
            ticker=r.ticker,
            score=r.score,
            price_change_pct=r.price_change_pct,
            volume_z=r.volume_z,
            news_count=r.news_count,
            rank=i + 1,
        )
        for i, r in enumerate(ranked)
    ]
    return IssuesTodayRes(as_of=now, window_hours=wh, items=items)
