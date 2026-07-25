"""admin 도메인 서비스 — 통합 설정(ConfigView) 조립 + 설정 변경."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin import repository as repo
from app.domains.admin.models import Keyword, SourceToggle, Stock
from app.domains.admin.schemas import ConfigView, StockOut


async def build_config(session: AsyncSession) -> ConfigView:
    """워커용 통합 설정 — 활성(enabled)만."""
    stocks = [
        StockOut(ticker=s.ticker, name=s.name, sector=s.sector, enabled=s.enabled)
        for s in await repo.list_stocks(session)
        if s.enabled
    ]
    keywords = [k.term for k in await repo.list_keywords(session) if k.enabled]
    sources = await repo.list_sources(session)
    period = (await repo.get_settings(session)).period
    return ConfigView(stocks=stocks, keywords=keywords, sources=sources, period=period)


async def set_stock_enabled(session: AsyncSession, ticker: str, enabled: bool) -> Stock | None:
    stock = await repo.get_stock(session, ticker)
    if stock is None:
        return None
    stock.enabled = enabled
    await session.commit()
    return stock


async def add_keyword(session: AsyncSession, term: str) -> Keyword:
    kw = Keyword(term=term, enabled=True)
    session.add(kw)
    await session.commit()
    await session.refresh(kw)
    return kw


async def set_keyword_enabled(session: AsyncSession, kid: int, enabled: bool) -> Keyword | None:
    kw = await repo.get_keyword(session, kid)
    if kw is None:
        return None
    kw.enabled = enabled
    await session.commit()
    return kw


async def delete_keyword(session: AsyncSession, kid: int) -> bool:
    kw = await repo.get_keyword(session, kid)
    if kw is None:
        return False
    await session.delete(kw)
    await session.commit()
    return True


async def set_source(session: AsyncSession, name: str, enabled: bool) -> SourceToggle:
    src = await repo.get_source(session, name)
    if src is None:
        src = SourceToggle(name=name, enabled=enabled)
        session.add(src)
    else:
        src.enabled = enabled
    await session.commit()
    return src


async def set_period(session: AsyncSession, period: str) -> str:
    settings_row = await repo.get_settings(session)
    settings_row.period = period
    await session.commit()
    return period
