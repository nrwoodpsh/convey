"""research Kafka 소비 — research.ingested 수신 → 사실 저장 + 관계추출 + 그래프 upsert. 라운드①.

파이프라인: news-feed(규칙 태깅) → research.ingested → [여기]
  Article 저장(Postgres) + LLM 관계추출(허용 엔티티만) + Neo4j upsert(근거 결속).
가드레일: 관계는 근거 기사(article.id)에 결속. 수치는 만들지 않음(사실은 Postgres).

`handle_ingested`(핵심 처리)는 실 PG+Neo4j+Ollama로 검증됨.
`run_consumer`(Kafka 전송 루프 + llm-inference 라우팅)는 표준 배선 — 전 스택 기동 시 e2e 검증.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx
from common.kafka import consume_forever
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from common.stocks import STOCK_NAMES, sector_of
from neo4j import GraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.domains.research.models import Article
from app.domains.research.repository import article_exists, upsert_macro, upsert_price_tick
from app.extract.relations import extract_graph
from app.graph.neo4j_repo import GraphRepo

logger = logging.getLogger("research.consumer")

_STOCK_NAMES_SET = set(STOCK_NAMES.values())  # 종목명 집합(사건 엣지 대상 판정)


async def handle_ingested(
    event: dict[str, Any],
    session: AsyncSession,
    graph: GraphRepo,
    llm: Callable[[str], str],
) -> tuple[int, int]:
    """research.ingested 1건 처리 → (article_id, 생성된 엣지 수).

    멱등(㉚): 같은 source_url 재수신이면 skip(재저장·재NER 안 함 — 폴링 중복·Ollama 낭비 방지).
    신규: Article 저장 → 개방형 NER(엔티티+관계 1콜) → 엔티티 노드·관계 upsert(근거=article.id).
    """
    source_url = event["source_url"]
    if await article_exists(session, source_url):
        return -1, 0  # 이미 처리한 기사 — skip

    published = event.get("published_at")
    published_at = (
        datetime.fromisoformat(published) if isinstance(published, str) else datetime.now()
    )
    article = Article(
        title=event["title"],
        body=event["body"],
        source_url=source_url,
        license=event["license"],
        published_at=published_at,
        lang=event.get("lang", "ko"),
        tickers=list(event.get("tickers", [])),  # 태깅 종목 영속 → 종목 기준 회수(라운드⑧)
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    # 개방형 NER(㉚) — 엔티티+관계 1콜. 사전 엔티티(seed) 합집. 동기 LLM은 스레드로 오프로드.
    entities = event.get("entities", [])
    g = await asyncio.to_thread(extract_graph, event["body"], entities, llm)
    for ent in g.entities:
        await asyncio.to_thread(graph.upsert_entity, ent, source_article_id=article.id)
    for rel in g.relations:
        await asyncio.to_thread(
            graph.upsert_relation, rel.subject, rel.edge, rel.object,
            source_article_id=article.id,
        )
    relations = g.relations

    # 결정론적 그래프 엣지(LLM 미개입·근거=article):
    #  - 종목→섹터 BELONGS_TO (㉕/A3)  - 종목→사건 HAS_EVENT (㉙/E3, DART 공시 등 event_hints)
    event_hints = [str(h) for h in event.get("event_hints", [])]
    det_edges = 0
    for ent in entities:
        e = str(ent)
        sector = sector_of(e)
        if sector:
            await asyncio.to_thread(
                graph.upsert_relation, e, "BELONGS_TO", sector, source_article_id=article.id,
            )
            det_edges += 1
        if sector_of(e) or e in _STOCK_NAMES_SET:  # 종목 엔티티면 사건 엣지
            for hint in event_hints:
                await asyncio.to_thread(
                    graph.upsert_relation, e, "HAS_EVENT", hint, source_article_id=article.id,
                )
                det_edges += 1

    logger.info(
        "research.ingested 처리: article=%s relations=%s det_edges=%s",
        article.id, len(relations), det_edges,
    )
    return article.id, len(relations) + det_edges


async def handle_tick(event: dict[str, Any], session: AsyncSession) -> tuple[int, bool]:
    """market.ticks 1건 처리 → PriceTick 멱등 저장(사실). 반환 (price_tick_id, created).

    시세는 사실(Postgres)로만 저장 — 그래프/LLM 미경유(수치는 만들지 않음, 가드레일).
    """
    ts_raw = event.get("ts")
    ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else datetime.now()
    return await upsert_price_tick(
        session,
        ticker=event["ticker"],
        ts=ts,
        open_=float(event["open"]),
        high=float(event["high"]),
        low=float(event["low"]),
        close=float(event["close"]),
        volume=int(event["volume"]),
    )


async def handle_macro(event: dict[str, Any], session: AsyncSession) -> tuple[int, bool]:
    """research.macro 1건 처리 → MacroIndicator 멱등 저장(사실). 반환 (id, created).

    거시는 그래프/LLM 미경유(사실만). 가드레일: source_url 없으면 저장 안 함.
    """
    if not event.get("source_url"):
        logger.warning("무출처 거시 이벤트 스킵: %s", event.get("name"))
        return -1, False
    as_of_raw = event.get("as_of")
    as_of = (
        datetime.fromisoformat(as_of_raw)
        if isinstance(as_of_raw, str)
        else datetime.now(timezone.utc)
    )
    return await upsert_macro(
        session,
        name=str(event["name"]),
        value=float(event["value"]),
        unit=str(event.get("unit", "")),
        as_of=as_of,
        source=str(event["source"]),
        source_url=str(event["source_url"]),
    )


def _llm_caller() -> Callable[[str], str]:
    """관계추출용 LLM 호출 — llm-inference 경유(로컬 Ollama). 게이트웨이 HMAC 신뢰헤더 서명."""

    def call(prompt: str) -> str:
        ts, sig = sign_internal(
            secret=settings.gateway_internal_secret, user_id="research-consumer", path="/generate"
        )
        resp = httpx.post(
            f"{settings.llm_inference_url}/generate",
            json={"prompt": prompt},
            headers={H_USER_ID: "research-consumer", H_TIMESTAMP: ts, H_SIGNATURE: sig},
            timeout=240,
        )
        return str(resp.json().get("response", ""))

    return call


async def run_consumer() -> None:
    """lifespan 백그라운드 진입점 — research.ingested를 소비해 handle_ingested로 처리.

    (전송 계층 표준 배선. 전 스택[Kafka·llm-inference] 기동 시 e2e 검증.)
    """
    user, _, pw = settings.neo4j_auth.partition("/")
    graph = GraphRepo(GraphDatabase.driver(settings.neo4j_url, auth=(user, pw)))
    llm = _llm_caller()

    async def handler(event: dict[str, Any]) -> None:
        async with SessionLocal() as session:
            await handle_ingested(event, session, graph, llm)

    await consume_forever(
        topic=settings.topic_ingested,
        group_id=settings.consumer_group,
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )


async def run_tick_consumer() -> None:
    """lifespan 백그라운드 진입점 — market.ticks를 소비해 PriceTick(사실) 멱등 저장.

    시세 스트림은 그래프/LLM을 거치지 않는다(사실만). market-feed(pykrx) → 여기 → research_db.
    """

    async def handler(event: dict[str, Any]) -> None:
        async with SessionLocal() as session:
            await handle_tick(event, session)

    await consume_forever(
        topic=settings.topic_ticks,
        group_id=f"{settings.consumer_group}-ticks",
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )


async def run_macro_consumer() -> None:
    """lifespan 백그라운드 진입점 — research.macro를 소비해 MacroIndicator(사실) 멱등 저장.

    거시 스트림은 그래프/LLM을 거치지 않는다(사실만). news-feed(ECOS·FRED) → 여기 → research_db.
    """

    async def handler(event: dict[str, Any]) -> None:
        async with SessionLocal() as session:
            await handle_macro(event, session)

    await consume_forever(
        topic=settings.topic_macro,
        group_id=f"{settings.consumer_group}-macro",
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )
