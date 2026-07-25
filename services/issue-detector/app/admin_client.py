"""admin 관심목록 조회(㉝ P4) — GET /admin/config를 east-west(HMAC)로 읽어 이슈 발행 게이팅.

활성 종목(watchlist)만 issue.selected로 발행. 실패 시 None → 게이팅 없음(폴백, 전량 발행).
Database per Service — admin_db 직접접근 금지, API만.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.config import settings

logger = logging.getLogger("issue-detector.admin")


def fetch_config() -> dict[str, Any] | None:
    """admin /admin/config 조회. 실패(연결·비200)면 None(게이팅 없음)."""
    path = "/admin/config"
    ts, sig = sign_internal(
        secret=settings.gateway_internal_secret, user_id="issue-detector", path=path
    )
    try:
        resp = httpx.get(
            f"{settings.admin_url}{path}",
            headers={H_USER_ID: "issue-detector", H_TIMESTAMP: ts, H_SIGNATURE: sig},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data: dict[str, Any] = resp.json()
        return data
    except httpx.HTTPError as exc:
        logger.warning("admin config 조회 실패(게이팅 없음): %s", exc)
        return None


def watchlist_tickers(config: dict[str, Any]) -> set[str]:
    """관심 종목 티커 집합(활성) — config.stocks는 활성만 담김(ConfigView)."""
    return {str(s["ticker"]) for s in config.get("stocks", []) if s.get("ticker")}
