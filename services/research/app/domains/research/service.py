"""research 서비스 계층 — 근거 회수(GraphRAG: Neo4j 관계 + Postgres 사실). ADR 0005·0006.

agent가 east-west로 /search 호출(저장소 직접접근 금지, 벡터 아님).
가드레일: 모든 fact·relation은 source_url 동반(무출처 제거).
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.research import repository
from app.domains.research.schemas import (
    FactHit,
    MacroHit,
    PriceEvidence,
    RelationHit,
    SearchResponse,
)
from app.graph.neo4j_repo import GraphRepo


async def search(
    session: AsyncSession,
    graph: GraphRepo,
    query: str,
    *,
    entity: str | None = None,
    ticker: str | None = None,
    top_k: int = 4,
    hops: int = 2,
    window_days: int | None = None,
) -> SearchResponse:
    """그래프 관계(Neo4j, 최대 hops홉) + SQL 사실(Postgres, window_days 기간)을 합쳐 근거를 반환."""
    # 사실 (Postgres SQL) — ticker 있으면 종목 태깅 기사 우선 + 키워드 보충(dedup, 라운드⑧)
    if ticker:
        by_ticker = await repository.fact_search_by_ticker(
            session, ticker, top_k, window_days=window_days
        )
        by_keyword = await repository.fact_search(session, query, top_k, window_days=window_days)
        seen: set[int] = set()
        fact_rows: list[tuple[int, str, str]] = []
        for fr in [*by_ticker, *by_keyword]:
            if fr[0] in seen:
                continue
            seen.add(fr[0])
            fact_rows.append(fr)
        fact_rows = fact_rows[:top_k]
    else:
        fact_rows = await repository.fact_search(session, query, top_k, window_days=window_days)
    facts = [
        FactHit(kind="article", text=title, source_url=url, ref_id=aid)
        for (aid, title, url) in fact_rows
    ]
    # 관계 (Neo4j traversal — 동기 드라이버는 스레드로 감싸 이벤트루프 비블로킹)
    ent = entity or query
    rel_rows = await asyncio.to_thread(graph.relations_of, ent, hops=hops)
    # 관계 근거 URL 해석 (source_article_id → Article.source_url)
    article_ids = list({aid for (_, _, _, aid) in rel_rows})
    url_map = await repository.source_urls_for(session, article_ids)
    relations = [
        RelationHit(
            subject=s, edge=e, object=o, source_article_id=aid, source_url=url_map.get(aid, "")
        )
        for (s, e, o, aid) in rel_rows
    ]
    # 가드레일: 무출처 제거
    facts = [f for f in facts if f.source_url]
    relations = [r for r in relations if r.source_url]
    # 가격 근거 (ticker 한정 시) — PriceTick 사실에서 최신 종가·등락률·시계열
    price: PriceEvidence | None = None
    if ticker:
        row = await repository.latest_price(session, ticker)
        if row is not None:
            ref_id, close, change_pct, series, source_url = row
            price = PriceEvidence(
                ticker=ticker, close=close, change_pct=change_pct,
                series=series, source_url=source_url, ref_id=ref_id,
            )
    # 거시 맥락 (각 name별 최신) — 종목 무관 전역 사실. 무출처 제거.
    macro_rows = await repository.latest_macros(session)
    macros = [
        MacroHit(
            name=name, value=value, unit=unit, as_of=as_of,
            source=source, source_url=url, ref_id=mid,
        )
        for (mid, name, value, unit, as_of, source, url) in macro_rows
        if url
    ]
    return SearchResponse(
        query=query, entity=ent, facts=facts, relations=relations, price=price, macros=macros
    )
