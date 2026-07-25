"""그래프 백필(㉕/A3·㉙/E3) — 기존 articles에서 그래프 엣지를 재생성한다.

기본(결정론): 종목→섹터 BELONGS_TO (Ollama 불필요·빠름).
--llm: 과거 기사에 개방형 NER 재실행(extract_article_graph — 긴 본문은 요약 선행, ㉛). Ollama, 재개 가능.
근거=article.id(무출처 아님). 사람이 실행:
  docker compose exec research python -m app.backfill            # 결정론만
  docker compose exec research python -m app.backfill --llm --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Callable

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from common.stocks import ENTITY_NAMES, sector_of, stock_name
from neo4j import GraphDatabase
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.domains.research.models import Article
from app.extract.relations import SUMMARY_NUM_PREDICT, extract_article_graph
from app.graph.neo4j_repo import GraphRepo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research.backfill")


def _llm_caller(num_predict: int | None = None) -> Callable[[str], str]:
    """num_predict 지정 시 출력 상한 전달(㉛ 요약용). 미지정이면 기존과 동일."""

    def call(prompt: str) -> str:
        ts, sig = sign_internal(
            secret=settings.gateway_internal_secret, user_id="backfill", path="/generate"
        )
        # think=False: 추론모델 <think> 억제(㉛). keep_alive: 모델 상주(재적재 방지).
        payload: dict[str, object] = {"prompt": prompt, "think": False, "keep_alive": "30m"}
        if num_predict is not None:
            payload["num_predict"] = num_predict
        resp = httpx.post(
            f"{settings.llm_inference_url}/generate",
            json=payload,
            headers={H_USER_ID: "backfill", H_TIMESTAMP: ts, H_SIGNATURE: sig},
            timeout=240,
        )
        return str(resp.json().get("response", ""))

    return call


async def run(*, use_llm: bool, limit: int) -> None:
    user, _, pw = settings.neo4j_auth.partition("/")
    graph = GraphRepo(GraphDatabase.driver(settings.neo4j_url, auth=(user, pw)))
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Article.id, Article.body, Article.tickers).order_by(Article.id.desc())
            )
        ).all()
    if limit > 0:
        rows = rows[:limit]

    sector_edges = rel_edges = 0
    # 직렬·저부하 유지(병렬화 금지 — Ollama 포화 방지, ㉛). NER(무제한) + 요약(출력 상한).
    llm = _llm_caller() if use_llm else None
    llm_summary = _llm_caller(SUMMARY_NUM_PREDICT) if use_llm else None
    for aid, body, tickers in rows:
        # 결정론: 종목→섹터
        for ticker in tickers or []:
            name = stock_name(str(ticker))
            sector = sector_of(name)
            if name and sector:
                graph.upsert_relation(name, "BELONGS_TO", sector, source_article_id=int(aid))
                sector_edges += 1
        # LLM: 개방형 NER — 긴 본문은 요약 선행(㉛). 사전 seed 합집, 검증은 원문(extract_article_graph 내부).
        if llm is not None and llm_summary is not None and body:
            seed = [n for n in ENTITY_NAMES if n in body]
            try:
                g = extract_article_graph(body, seed, llm, llm_summary)
                for ent in g.entities:
                    et, dr = g.events.get(ent, ("", ""))  # ㉟ 사건 속성
                    graph.upsert_entity(
                        ent, source_article_id=int(aid),
                        node_type=g.types.get(ent, ""), event_type=et, direction=dr,
                    )
                for r in g.relations:
                    graph.upsert_relation(r.subject, r.edge, r.object, source_article_id=int(aid))
                    rel_edges += 1
            except Exception:  # noqa: BLE001 — 개별 기사 실패는 건너뜀(재개 가능)
                logger.exception("개방형 추출 실패 article=%s", aid)
    logger.info(
        "백필 완료: 기사 %s건 · 섹터엣지 %s · 관계엣지 %s (llm=%s)",
        len(rows), sector_edges, rel_edges, use_llm,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="과거 기사 LLM 관계추출까지(느림)")
    ap.add_argument("--limit", type=int, default=0, help="처리 기사 수 상한(0=전체)")
    args = ap.parse_args()
    asyncio.run(run(use_llm=args.llm, limit=args.limit))


if __name__ == "__main__":
    main()
