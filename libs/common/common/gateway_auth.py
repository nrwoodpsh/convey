"""하류 서비스가 '게이트웨이 경유' 요청만 신뢰하도록 하는 FastAPI 의존성.

각 서비스가 자신의 internal_secret으로 팩토리를 만들어 라우터에 주입한다:

    gateway_user = make_gateway_dep(settings.gateway_internal_secret)

    @router.get("/items")
    async def list_items(user: UserContext = Depends(gateway_user)): ...
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from .errors import AppError
from .security import (
    H_SIGNATURE,
    H_TIMESTAMP,
    H_USER_ID,
    H_USER_NAME,
    H_USER_ROLES,
    UserContext,
    verify_internal,
)


def make_gateway_dep(secret: str) -> Callable[[Request], UserContext]:
    def dependency(request: Request) -> UserContext:
        user_id = request.headers.get(H_USER_ID)
        ts = request.headers.get(H_TIMESTAMP)
        sig = request.headers.get(H_SIGNATURE)
        if not (user_id and ts and sig):
            raise AppError("forbidden", "게이트웨이 신뢰헤더 없음", status=403)
        if not verify_internal(
            secret=secret, user_id=user_id, path=request.url.path, ts=ts, signature=sig
        ):
            raise AppError("forbidden", "게이트웨이 서명 검증 실패", status=403)
        return UserContext(
            user_id=user_id,
            user_name=request.headers.get(H_USER_NAME, ""),
            roles=request.headers.get(H_USER_ROLES, ""),
        )

    return dependency
