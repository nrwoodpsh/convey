"""admin 설정 조회(㉝ P3) — GET /admin/config를 east-west(HMAC)로 읽어 수집에 반영.

Database per Service — admin_db 직접접근 금지, API만. 실패 시 None → 호출부가 하드코딩 폴백.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.config import settings

logger = logging.getLogger("news-feed.admin")

_SOURCES = ("naver", "rss", "dart")


def fetch_config() -> dict[str, Any] | None:
    """admin /admin/config 조회. 실패(연결·비200)면 None(폴백 유도)."""
    path = "/admin/config"
    ts, sig = sign_internal(
        secret=settings.gateway_internal_secret, user_id="news-feed", path=path
    )
    try:
        resp = httpx.get(
            f"{settings.admin_url}{path}",
            headers={H_USER_ID: "news-feed", H_TIMESTAMP: ts, H_SIGNATURE: sig},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data: dict[str, Any] = resp.json()
        return data
    except httpx.HTTPError as exc:
        logger.warning("admin config 조회 실패(폴백): %s", exc)
        return None


def derive_queries(config: dict[str, Any]) -> list[str]:
    """검색어 = 활성 종목명 + 등록 키워드(㉝). config는 활성만 담김(ConfigView)."""
    names = [str(s["name"]) for s in config.get("stocks", []) if s.get("name")]
    keywords = [str(k) for k in config.get("keywords", []) if str(k).strip()]
    out: list[str] = []
    for q in names + keywords:  # 순서 유지·중복 제거
        if q not in out:
            out.append(q)
    return out


def source_enabled(config: dict[str, Any], name: str) -> bool:
    """소스 토글 — 설정에 없으면 기본 ON."""
    sources = config.get("sources", {})
    return bool(sources.get(name, True))
