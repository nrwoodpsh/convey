"""대시보드 지표·근거 조립(㊵ M2) — 여러 서비스 데이터를 화면 뷰모델로.

지표(품질): 그래프 규모(research)·오늘 기사(research)·오늘 이슈(issue-detector)·완성 잡(content local).
근거(신뢰·알파①): content가 저장한 Script의 관계·출처·수치를 EvidenceView로.
모든 원격 호출은 east-west(HMAC), 실패는 관대(0·빈 목록) — 대시보드는 치명 아님.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from sqlalchemy.ext.asyncio import AsyncSession

from app import research_client
from app.config import settings
from app.domains.content import repository

logger = logging.getLogger("content.dashboard")

_READY_STATUSES = ("ready", "approved")  # 완성(발행 대기) 잡


async def _fetch_issue_count() -> int:
    """issue-detector GET /issues/today → 오늘 이슈 수. 실패 시 0."""
    path = "/issues/today"
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="content", path=path)
    headers = {H_USER_ID: "content", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.issue_detector_url.rstrip('/')}{path}", headers=headers
            )
            resp.raise_for_status()
            return len(resp.json().get("items", []))
    except Exception:  # noqa: BLE001 — 지표 실패는 0(대시보드 관대)
        logger.warning("이슈 수 회수 실패")
        return 0


async def gather_metrics(session: AsyncSession) -> dict[str, int]:
    """품질 지표(㊵/AC4) — 그래프·기사·이슈·완성 잡. 각 실패는 0."""
    by_status, _ = await repository.stats(session)
    jobs_ready = sum(by_status.get(s, 0) for s in _READY_STATUSES)
    articles = await research_client.fetch_articles(window_days=1, limit=200)
    nodes, relations = await research_client.fetch_graph_stats()
    issues = await _fetch_issue_count()
    return {
        "graph_nodes": nodes,
        "graph_relations": relations,
        "articles_today": len(articles),
        "issues_selected": issues,
        "jobs_ready": jobs_ready,
    }


def build_evidence(script_sections: list[dict[str, Any]], citations: list[dict[str, Any]]) -> dict[str, list[str]]:
    """저장된 Script → 근거 뷰(㊵/AC3) — 관계·출처·수치. 순수 함수(테스트 용이).

    관계=relation 섹션 텍스트, 출처=citation source_url(중복 제거·순서 보존),
    수치=chart 섹션 텍스트(data_slots로 {close} 등 사실값 치환 — 환각 아닌 저장된 수치).
    """
    relations = [str(s.get("text", "")) for s in script_sections if s.get("kind") == "relation"]
    prices: list[str] = []
    for s in script_sections:
        if s.get("kind") != "chart":
            continue
        text = str(s.get("text", ""))
        slots = s.get("data_slots") or {}
        try:
            text = text.format(**slots)  # {close}→사실값(저장된 수치, 알파①)
        except (KeyError, IndexError, ValueError):
            pass
        prices.append(text)
    seen: set[str] = set()
    sources: list[str] = []
    for c in citations:
        url = str(c.get("source_url", ""))
        if url and url not in seen:
            seen.add(url)
            sources.append(url)
    return {"relations": relations, "sources": sources, "prices": prices}
