"""FastAPI 게이트웨이 — 단일 외부 진입점.

흐름:
1. 공개 경로가 아니면 Bearer JWT 검증.
2. 클라이언트가 위조했을 수 있는 신뢰헤더를 제거(StripTrustHeaders).
3. 사용자 컨텍스트 헤더 + HMAC 서명을 붙여 하류로 프록시.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from common.errors import register_exception_handlers
from common.logging import configure_logging
from common.security import (
    H_SIGNATURE,
    H_TIMESTAMP,
    H_USER_ID,
    H_USER_NAME,
    H_USER_ROLES,
    decode_token,
    sign_internal,
)
from fastapi import FastAPI, Request, Response

from app.config import PUBLIC_PATHS, settings

configure_logging(settings.log_level)
logger = logging.getLogger("gateway")

# 하류로 흘러들면 안 되는(클라이언트 위조 가능) 신뢰헤더
_STRIP = {h.lower() for h in (H_USER_ID, H_USER_NAME, H_USER_ROLES, H_TIMESTAMP, H_SIGNATURE)}
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="gateway", lifespan=lifespan)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _resolve(path: str) -> tuple[str, str] | None:
    """path → (target_base, downstream_path). prefix 제거 후 하류 경로 생성."""
    for prefix, base in settings.routes.items():
        if path == prefix or path.startswith(prefix + "/"):
            downstream = path[len(prefix):] or "/"
            return base, downstream
    return None


def _authenticate(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        from common.errors import AppError

        raise AppError("unauthorized", "인증 토큰 없음", status=401)
    try:
        return decode_token(auth[7:], secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    except Exception as exc:  # noqa: BLE001
        from common.errors import AppError

        raise AppError("unauthorized", "토큰 검증 실패", status=401) from exc


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request) -> Response:
    from common.errors import AppError

    path = "/" + full_path
    resolved = _resolve(path)
    if resolved is None:
        raise AppError("not_found", f"라우트 없음: {path}", status=404)
    base, downstream = resolved

    # 1) 헤더 정리: hop-by-hop + 클라이언트 위조 신뢰헤더 제거
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP and k.lower() not in _STRIP
    }

    # 2) 인증 + 신뢰헤더 주입
    if path not in PUBLIC_PATHS:
        claims = _authenticate(request)
        user_id = str(claims.get("sub", ""))
        ts, sig = sign_internal(
            secret=settings.gateway_internal_secret, user_id=user_id, path=downstream
        )
        headers[H_USER_ID] = user_id
        headers[H_USER_NAME] = str(claims.get("name", ""))
        headers[H_USER_ROLES] = str(claims.get("roles", ""))
        headers[H_TIMESTAMP] = ts
        headers[H_SIGNATURE] = sig

    client: httpx.AsyncClient = request.app.state.client
    body = await request.body()
    upstream = await client.request(
        request.method,
        base + downstream,
        params=request.query_params,
        headers=headers,
        content=body,
    )
    resp_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=upstream.content, status_code=upstream.status_code, headers=resp_headers
    )
