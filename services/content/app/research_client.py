"""research east-west 클라이언트(라운드㉓) — 대시보드용 오늘자 수집 기사 회수.

대시보드(무인증 /ui)는 research_db에 직접 접근하지 않는다(도메인 경계·저장소 직접접근 금지).
research `GET /research/articles`를 HMAC 서명으로 호출한다(agent retriever와 동일 패턴).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.config import settings

logger = logging.getLogger("content.research_client")


async def fetch_articles(*, window_days: int, limit: int) -> list[dict[str, Any]]:
    """research /research/articles 호출 → 기사 목록(dict). 실패 시 빈 목록(대시보드 관대)."""
    path = "/research/articles"
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="content", path=path)
    headers = {H_USER_ID: "content", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    params = {"window_days": window_days, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.research_url.rstrip('/')}{path}", params=params, headers=headers
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            items = data.get("items", [])
            return list(items)
    except Exception:  # noqa: BLE001 — 대시보드 조회 실패는 빈 목록으로(치명 아님)
        logger.exception("기사 목록 회수 실패 window=%s", window_days)
        return []
