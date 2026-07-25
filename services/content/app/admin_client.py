"""admin 시나리오 템플릿 조회(㊳) — 대본 생성 시 template_id로 노브 정의를 가져온다.

content가 admin_db를 직접 보지 않고 API로만 읽는다(Database per Service). 실패·미지정 시 None →
agent가 기본(분석형)으로 생성(하위호환, AC4).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.config import settings

logger = logging.getLogger("content.admin")

# agent TemplateDefIn에 전달할 노브 키(수치·관계는 Evidence, 알파① — 여기엔 구조·톤만)
_KNOB_KEYS = ("n_facts", "n_relations", "use_macro", "use_closing", "hook_tone")


async def fetch_template_def(template_id: int) -> dict[str, Any] | None:
    """admin GET /admin/templates/{id} → agent에 넘길 노브 dict. 실패 시 None(기본형 폴백)."""
    path = f"/admin/templates/{template_id}"
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="content", path=path)
    headers = {H_USER_ID: "content", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.admin_url.rstrip('/')}{path}", headers=headers)
        if resp.status_code != 200:
            return None
        t: dict[str, Any] = resp.json()
        return {k: t[k] for k in _KNOB_KEYS if k in t}
    except httpx.HTTPError as exc:
        logger.warning("템플릿 조회 실패(기본형 폴백) id=%s: %s", template_id, exc)
        return None


async def admin_request(
    method: str, path: str, *, json: Any | None = None, params: dict[str, Any] | None = None
) -> tuple[int, Any]:
    """admin API 제네릭 중계(㊵ 설정 프록시) — HMAC 서명 후 그대로 전달. (status, body) 반환.

    대시보드 설정 탭이 admin(㉝·㊳·㊴) CRUD를 content 경유로 호출(Database per Service).
    실패(연결 등)는 (502, {}) — content가 admin_db를 직접 보지 않는다.
    """
    ts, sig = sign_internal(secret=settings.gateway_internal_secret, user_id="dashboard", path=path)
    headers = {H_USER_ID: "dashboard", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(
                method, f"{settings.admin_url.rstrip('/')}{path}",
                json=json, params=params, headers=headers,
            )
        body: Any = resp.json() if resp.content else None
        return resp.status_code, body
    except httpx.HTTPError as exc:
        logger.warning("admin 중계 실패 %s %s: %s", method, path, exc)
        return 502, {}
