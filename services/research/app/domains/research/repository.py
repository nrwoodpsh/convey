"""research 저장소 계층(Postgres 사실) — Article·PriceTick 조회.

관계·인과 그래프(Neo4j)는 GraphRepo(app/graph)에서 다룬다.
가드레일: Article.source_url은 NOT NULL이라 회수 결과는 항상 출처를 동반(무출처 0).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.research.models import Article, MacroIndicator, PriceTick


async def article_exists(session: AsyncSession, source_url: str) -> bool:
    """수집 멱등(㉚) — 같은 source_url 기사가 이미 있으면 True(재저장·재NER skip)."""
    row = (
        await session.execute(
            select(Article.id).where(Article.source_url == source_url).limit(1)
        )
    ).first()
    return row is not None


async def list_articles(
    session: AsyncSession, *, window_days: int, limit: int
) -> list[tuple[int, str, str, datetime, list[str]]]:
    """수집 기사 목록 — 최근 window_days, 최신순(published_at desc). 대시보드 선택용(㉓).

    반환 (id, title, source_url, published_at, tickers). 출처 없는 건 제외(가드레일).
    """
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    stmt = (
        select(Article.id, Article.title, Article.source_url, Article.published_at, Article.tickers)
        .where(Article.published_at >= since, Article.source_url != "")
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(r[0], r[1], r[2], r[3], list(r[4] or [])) for r in rows]


async def upsert_price_tick(
    session: AsyncSession,
    *,
    ticker: str,
    ts: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int,
) -> tuple[int, bool]:
    """market.ticks → PriceTick 멱등 저장. 반환 (id, created).

    market-feed가 같은 일봉을 반복 발행하므로 (ticker, ts) 동일하면 OHLCV만 갱신(장중 값
    수렴), 없으면 삽입. 가드레일: 값 조작 없이 이벤트 실측 그대로 저장.
    """
    existing = (
        await session.execute(
            select(PriceTick).where(PriceTick.ticker == ticker, PriceTick.ts == ts)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.open = open_
        existing.high = high
        existing.low = low
        existing.close = close
        existing.volume = volume
        await session.commit()
        return existing.id, False
    tick = PriceTick(
        ticker=ticker, ts=ts, open=open_, high=high, low=low, close=close, volume=volume
    )
    session.add(tick)
    await session.commit()
    await session.refresh(tick)
    return tick.id, True


async def fact_search(
    session: AsyncSession, query: str, top_k: int, *, window_days: int | None = None
) -> list[tuple[int, str, str]]:
    """키워드로 Article 회수(제목·본문 ILIKE). window_days 있으면 기간 필터. 반환 (id, title, source_url)."""
    like = f"%{query}%"
    stmt = select(Article.id, Article.title, Article.source_url).where(
        or_(Article.title.ilike(like), Article.body.ilike(like))
    )
    if window_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        stmt = stmt.where(Article.published_at >= since)
    stmt = stmt.order_by(Article.published_at.desc()).limit(top_k)
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]


def price_source_url(ticker: str) -> str:
    """가격 사실의 공개 출처(무출처 금지 가드레일). 시세 원천 = KRX(pykrx) — 정보데이터시스템.

    데이터 실제 출처가 KRX이므로 KRX 표기로 통일(라운드⑥ 정정, 네이버 아님).
    """
    return f"http://data.krx.co.kr/?isu_cd={ticker}"


async def latest_price(
    session: AsyncSession, ticker: str, *, window: int = 30
) -> tuple[int, float, float, list[float], str] | None:
    """종목 최신 시세 근거 → (ref_id, close, change_pct, series, source_url) 또는 None.

    최근 `window`개 종가를 오름차순 시계열로, 등락률은 직전 거래일 대비. 값 조작 없이 실측만.
    """
    rows = (
        await session.execute(
            select(PriceTick.id, PriceTick.ts, PriceTick.close)
            .where(PriceTick.ticker == ticker)
            .order_by(PriceTick.ts.desc())
            .limit(window)
        )
    ).all()
    if not rows:
        return None
    rows = list(reversed(rows))  # 시간 오름차순
    series = [float(r[2]) for r in rows]
    last_id = int(rows[-1][0])
    close = series[-1]
    change_pct = (close - series[-2]) / series[-2] * 100 if len(series) >= 2 and series[-2] else 0.0
    return last_id, close, change_pct, series, price_source_url(ticker)


async def upsert_macro(
    session: AsyncSession,
    *,
    name: str,
    value: float,
    unit: str,
    as_of: datetime,
    source: str,
    source_url: str,
) -> tuple[int, bool]:
    """거시 지표 멱등 저장 → (id, created). 같은 (name, as_of, source)면 값 갱신, 없으면 삽입.

    값은 이벤트 실측 그대로(조작 0). 반복 폴링 중복 방지.
    """
    existing = (
        await session.execute(
            select(MacroIndicator).where(
                MacroIndicator.name == name,
                MacroIndicator.as_of == as_of,
                MacroIndicator.source == source,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.value = value
        existing.unit = unit
        existing.source_url = source_url
        await session.commit()
        return existing.id, False
    row = MacroIndicator(
        name=name, value=value, unit=unit, as_of=as_of, source=source, source_url=source_url
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row.id, True


async def latest_macros(
    session: AsyncSession, *, limit: int = 20
) -> list[tuple[int, str, float, str, datetime, str, str]]:
    """각 name별 최신 거시 1건 → (id, name, value, unit, as_of, source, source_url).

    Postgres DISTINCT ON (name) + ORDER BY name, as_of DESC. 값은 저장 그대로(조작 0).
    """
    stmt = (
        select(
            MacroIndicator.id, MacroIndicator.name, MacroIndicator.value,
            MacroIndicator.unit, MacroIndicator.as_of, MacroIndicator.source,
            MacroIndicator.source_url,
        )
        .distinct(MacroIndicator.name)
        .order_by(MacroIndicator.name, MacroIndicator.as_of.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows]


async def fact_search_by_ticker(
    session: AsyncSession, ticker: str, top_k: int, *, window_days: int | None = None
) -> list[tuple[int, str, str]]:
    """종목 태깅 기사 회수 — `tickers @> [ticker]`(JSONB). 검색어 문자열과 무관하게 정확 회수.

    반환 (id, title, source_url). 최신순.
    """
    stmt = select(Article.id, Article.title, Article.source_url).where(
        Article.tickers.contains([ticker])
    )
    if window_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        stmt = stmt.where(Article.published_at >= since)
    stmt = stmt.order_by(Article.published_at.desc()).limit(top_k)
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]


async def source_urls_for(session: AsyncSession, ids: list[int]) -> dict[int, str]:
    """기사 id → source_url. 그래프 관계의 근거 기사 URL 해석에 사용."""
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(Article.id, Article.source_url).where(Article.id.in_(ids))
        )
    ).all()
    return {row[0]: row[1] for row in rows}
