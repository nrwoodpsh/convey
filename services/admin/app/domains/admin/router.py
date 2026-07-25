"""admin API — 대시보드 쓰기·워커 읽기. 게이트웨이 HMAC 신뢰헤더 필요(east-west)."""
from __future__ import annotations

from common.errors import AppError
from common.gateway_auth import make_gateway_dep
from common.security import UserContext
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.domains.admin import service
from app.domains.admin.repository import get_settings, list_keywords, list_sources, list_stocks
from app.domains.admin.schemas import (
    ConfigView,
    KeywordIn,
    KeywordOut,
    KeywordToggle,
    PeriodIn,
    SourceIn,
    StockOut,
    StockToggle,
)

_dep = make_gateway_dep(settings.gateway_internal_secret)  # 게이트웨이 HMAC 신뢰헤더 검증

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config", response_model=ConfigView)
async def get_config(
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep)
) -> ConfigView:
    return await service.build_config(session)


@router.get("/stocks", response_model=list[StockOut])
async def stocks(
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep)
) -> list[StockOut]:
    return [
        StockOut(ticker=s.ticker, name=s.name, sector=s.sector, enabled=s.enabled)
        for s in await list_stocks(session)
    ]


@router.put("/stocks/{ticker}", response_model=StockOut)
async def toggle_stock(
    ticker: str, body: StockToggle,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> StockOut:
    s = await service.set_stock_enabled(session, ticker, body.enabled)
    if s is None:
        raise AppError("not_found", f"종목 없음: {ticker}", status=404)
    return StockOut(ticker=s.ticker, name=s.name, sector=s.sector, enabled=s.enabled)


@router.get("/keywords", response_model=list[KeywordOut])
async def keywords(
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep)
) -> list[KeywordOut]:
    return [KeywordOut(id=k.id, term=k.term, enabled=k.enabled) for k in await list_keywords(session)]


@router.post("/keywords", response_model=KeywordOut)
async def add_keyword(
    body: KeywordIn,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> KeywordOut:
    k = await service.add_keyword(session, body.term)
    return KeywordOut(id=k.id, term=k.term, enabled=k.enabled)


@router.put("/keywords/{kid}", response_model=KeywordOut)
async def toggle_keyword(
    kid: int, body: KeywordToggle,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> KeywordOut:
    k = await service.set_keyword_enabled(session, kid, body.enabled)
    if k is None:
        raise AppError("not_found", f"키워드 없음: {kid}", status=404)
    return KeywordOut(id=k.id, term=k.term, enabled=k.enabled)


@router.delete("/keywords/{kid}")
async def delete_keyword(
    kid: int,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> dict[str, bool]:
    ok = await service.delete_keyword(session, kid)
    if not ok:
        raise AppError("not_found", f"키워드 없음: {kid}", status=404)
    return {"deleted": True}


@router.put("/sources/{name}")
async def set_source(
    name: str, body: SourceIn,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> dict[str, bool]:
    src = await service.set_source(session, name, body.enabled)
    return {src.name: src.enabled}


@router.put("/settings/period")
async def set_period(
    body: PeriodIn,
    session: AsyncSession = Depends(get_session), _: UserContext = Depends(_dep),
) -> dict[str, str]:
    if body.period not in ("1w", "1m", "3m"):
        raise AppError("bad_request", "period는 1w|1m|3m", status=400)
    return {"period": await service.set_period(session, body.period)}
