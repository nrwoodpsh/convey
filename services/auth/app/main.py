"""auth 서비스 — 로그인/토큰 발급. (게이트웨이가 /auth prefix를 떼고 전달)

데모용 인메모리 사용자. 운영에선 사용자 스토어 + 비밀번호 해싱(passlib/bcrypt)으로 교체.
"""
from __future__ import annotations

from common.config import BaseAppSettings
from common.errors import AppError, register_exception_handlers
from common.gateway_auth import make_gateway_dep
from common.logging import configure_logging
from common.security import UserContext, create_token, decode_token
from fastapi import Depends, FastAPI
from pydantic import BaseModel

settings = BaseAppSettings()
configure_logging(settings.log_level)

app = FastAPI(title="auth")
register_exception_handlers(app)
gateway_user = make_gateway_dep(settings.gateway_internal_secret)

# 데모 사용자 — {username: (password, name, roles)}
_USERS: dict[str, tuple[str, str, str]] = {
    "demo": ("demo", "Demo User", "user"),
    "admin": ("admin", "Admin", "user,admin"),
}


class LoginReq(BaseModel):
    username: str
    password: str


class RefreshReq(BaseModel):
    refresh_token: str


class TokenResp(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _issue(username: str, name: str, roles: str) -> TokenResp:
    common = {"secret": settings.jwt_secret, "algorithm": settings.jwt_algorithm}
    access = create_token(
        subject=username, ttl_seconds=settings.access_ttl_seconds,
        extra={"name": name, "roles": roles, "typ": "access"}, **common,
    )
    refresh = create_token(
        subject=username, ttl_seconds=settings.refresh_ttl_seconds,
        extra={"typ": "refresh"}, **common,
    )
    return TokenResp(access_token=access, refresh_token=refresh)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/login", response_model=TokenResp)
async def login(req: LoginReq) -> TokenResp:
    row = _USERS.get(req.username)
    if not row or row[0] != req.password:
        raise AppError("invalid_credentials", "아이디/비밀번호 불일치", status=401)
    _, name, roles = row
    return _issue(req.username, name, roles)


@app.post("/refresh", response_model=TokenResp)
async def refresh(req: RefreshReq) -> TokenResp:
    try:
        claims = decode_token(
            req.refresh_token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError("invalid_token", "리프레시 토큰 오류", status=401) from exc
    if claims.get("typ") != "refresh":
        raise AppError("invalid_token", "리프레시 토큰 아님", status=401)
    username = str(claims.get("sub", ""))
    row = _USERS.get(username)
    if not row:
        raise AppError("invalid_token", "알 수 없는 사용자", status=401)
    _, name, roles = row
    return _issue(username, name, roles)


@app.get("/me")
async def me(user: UserContext = Depends(gateway_user)) -> dict[str, str]:
    """게이트웨이 신뢰헤더 검증 데모 — 직접 호출 시 403."""
    return {"user_id": user.user_id, "name": user.user_name, "roles": user.roles}
