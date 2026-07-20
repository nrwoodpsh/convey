"""research Kafka 소비 — research.ingested 수신 → 사실 저장 + 관계추출 + 그래프 upsert. 라운드①.

파이프라인: news-feed(규칙 태깅) → research.ingested → [여기]
  Article 저장(Postgres) + LLM 관계추출(허용 엔티티만) + Neo4j upsert(근거 결속).
가드레일: 관계는 근거 기사(article.id)에 결속. 수치는 만들지 않음(사실은 Postgres).

`handle_ingested`(핵심 처리)는 실 PG+Neo4j+Ollama로 검증됨.
`run_consumer`(Kafka 전송 루프 + llm-inference 라우팅)는 표준 배선 — 전 스택 기동 시 e2e 검증.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
from common.kafka import consume_forever
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from neo4j import GraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.domains.research.models import Article
from app.extract.relations import extract_relations
from app.graph.neo4j_repo import GraphRepo

logger = logging.getLogger("research.consumer")


async def handle_ingested(
    event: dict[str, Any],
    session: AsyncSession,
    graph: GraphRepo,
    llm: Callable[[str], str],
) -> tuple[int, int]:
    """research.ingested 1건 처리 → (article_id, 생성된 관계 수).

    1) Article 저장(출처·라이선스 필수)  2) 허용 엔티티로 LLM 관계추출  3) 그래프 upsert(근거=article.id)
    """
    published = event.get("published_at")
    published_at = (
        datetime.fromisoformat(published) if isinstance(published, str) else datetime.now()
    )
    article = Article(
        title=event["title"],
        body=event["body"],
        source_url=event["source_url"],
        license=event["license"],
        published_at=published_at,
        lang=event.get("lang", "ko"),
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    entities = event.get("entities", [])
    relations = extract_relations(event["body"], entities, llm) if entities else []
    for rel in relations:
        graph.upsert_relation(rel.subject, rel.edge, rel.object, source_article_id=article.id)

    logger.info("research.ingested 처리: article=%s relations=%s", article.id, len(relations))
    return article.id, len(relations)


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
