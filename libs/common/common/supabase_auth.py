"""Supabase JWT 검증 (JWKS 비대칭). ADR 0007 / 라운드0.

게이트웨이가 Supabase 발급 access token을 JWKS 공개키로 검증한다.
로그인·토큰 발급은 Supabase 소유 — 여기선 **검증 + UserContext 매핑**만 한다.
"""
from __future__ import annotations

from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from .errors import AppError
from .security import UserContext


class SigningKeyResolver(Protocol):
    """JWKS에서 토큰의 서명 키를 찾는 인터페이스 (PyJWKClient 호환, 테스트 주입용)."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class SupabaseVerifier:
    """Supabase access token 검증기 — 서명(JWKS) + audience + 만료 확인."""

    def __init__(
        self,
        jwks: SigningKeyResolver,
        *,
        audience: str,
        algorithms: list[str] | None = None,
    ) -> None:
        self._jwks = jwks
        self._audience = audience
        self._algorithms = algorithms or ["ES256", "RS256"]

    def verify(self, token: str) -> dict[str, Any]:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=self._algorithms,
                audience=self._audience,
            )
            return claims
        except jwt.ExpiredSignatureError as exc:
            raise AppError("AUTH003", "토큰 만료", status=401) from exc
        except jwt.InvalidAudienceError as exc:
            raise AppError("AUTH004", "잘못된 audience", status=401) from exc
        except jwt.PyJWTError as exc:
            raise AppError("AUTH002", "토큰 검증 실패", status=401) from exc


def build_verifier(jwks_url: str, audience: str) -> SupabaseVerifier:
    """운영용 — Supabase JWKS URL로 검증기 생성(키 캐시는 PyJWKClient가 담당)."""
    return SupabaseVerifier(PyJWKClient(jwks_url), audience=audience)


def claims_to_user(claims: dict[str, Any]) -> UserContext:
    """Supabase 클레임 → UserContext.

    계약(api-contract): sub→user_id · user_metadata.name(없으면 email)→user_name ·
    app_metadata.roles(CSV)→roles (없으면 role).
    """
    user_meta = claims.get("user_metadata") or {}
    app_meta = claims.get("app_metadata") or {}
    name = str(user_meta.get("name") or claims.get("email") or "")
    roles_val = app_meta.get("roles")
    if isinstance(roles_val, list):
        roles = ",".join(str(r) for r in roles_val)
    else:
        roles = str(roles_val or claims.get("role") or "")
    return UserContext(user_id=str(claims.get("sub", "")), user_name=name, roles=roles)
