"""그래프 백필(㉕/A3) — 기존 articles에서 종목→섹터 엣지를 재생성한다.

관계추출(LLM)은 실시간 소비에서만 돌고, 과거 기사는 그래프에 안 남아 있었다. 이 스크립트는
**결정론적 종목→섹터(BELONGS_TO)** 엣지를 과거 기사 전체에 대해 채운다(Ollama 불필요·빠름).
근거=article.id(무출처 아님). 사람이 실행: `docker compose exec research python -m app.backfill`.
"""
from __future__ import annotations

import asyncio
import logging

from common.stocks import sector_of, stock_name
from neo4j import GraphDatabase
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.domains.research.models import Article
from app.graph.neo4j_repo import GraphRepo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research.backfill")


async def run() -> None:
    user, _, pw = settings.neo4j_auth.partition("/")
    graph = GraphRepo(GraphDatabase.driver(settings.neo4j_url, auth=(user, pw)))
    edges = 0
    articles = 0
    async with SessionLocal() as session:
        rows = (await session.execute(select(Article.id, Article.tickers))).all()
    for aid, tickers in rows:
        seen: set[str] = set()
        for ticker in tickers or []:
            name = stock_name(str(ticker))
            sector = sector_of(name)
            if name and sector and name not in seen:
                seen.add(name)
                graph.upsert_relation(name, "BELONGS_TO", sector, source_article_id=int(aid))
                edges += 1
        if seen:
            articles += 1
    logger.info("백필 완료: 기사 %s건에서 종목→섹터 엣지 %s개 생성", articles, edges)


if __name__ == "__main__":
    asyncio.run(run())
