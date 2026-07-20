"""
API 계약 — 라운드 0: 인증 (Supabase Auth) · ADR 0007
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

핵심: 로그인·토큰 발급은 **Supabase가 소유**. 우리 API에 로그인 엔드포인트 없음.
게이트웨이가 Supabase JWT를 검증(JWKS)해 UserContext로 매핑 → 하류에 HMAC 신뢰헤더(원형 유지).
이 계약은 (1) 우리가 의존하는 Supabase JWT 클레임, (2) UserContext 매핑, (3) 에러를 고정한다.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# 1) 게이트웨이 검증 설정 (JWKS = 비대칭, 키 로테이션·시크릿 미보관)
#    .env: SUPABASE_URL, SUPABASE_JWKS_URL(기본 {URL}/auth/v1/.well-known/jwks.json), SUPABASE_AUD
SUPABASE_DEFAULT_AUD = "authenticated"


# 2) 우리가 의존하는 Supabase access token 클레임 (필요한 것만)
class SupabaseClaims(BaseModel):
    sub: str  # 사용자 UUID → user_id
    aud: str = Field(description="기본 'authenticated'")
    exp: int  # 만료 (epoch)
    email: str | None = None
    role: str | None = None  # 예: 'authenticated'
    app_metadata: dict[str, object] = Field(default_factory=dict)  # 권한(roles 등)
    user_metadata: dict[str, object] = Field(default_factory=dict)  # 프로필(name 등)


# 3) 하류로 넘기는 사용자 컨텍스트 (원형 common.security.UserContext와 정합)
class GatewayUserContext(BaseModel):
    user_id: str  # = claims.sub
    user_name: str = ""  # = user_metadata['name'] or email
    roles: str = ""  # CSV = app_metadata['roles'] 조인 (없으면 role)


# 4) 매핑 규칙(계약): sub→user_id · user_metadata.name(or email)→user_name · app_metadata.roles(CSV)→roles


# 5) 에러 레지스트리 (libs/common/common/errors.py와 정합)
class AuthError(tuple[str, int, str], Enum):
    NO_TOKEN = ("AUTH001", 401, "인증 토큰 없음")
    INVALID_TOKEN = ("AUTH002", 401, "토큰 검증 실패")
    EXPIRED = ("AUTH003", 401, "토큰 만료")
    WRONG_AUDIENCE = ("AUTH004", 401, "잘못된 audience")
    FORBIDDEN_DIRECT = ("AUTH005", 403, "게이트웨이 신뢰헤더 없음/서명 실패")


# 6) 제거 대상(계약상 명시): 우리 /auth/login·/auth/refresh 엔드포인트, services/auth, auth_db,
#    PUBLIC_PATHS의 /auth/login·/auth/refresh, JWT_SECRET. (GATEWAY_INTERNAL_SECRET·HMAC은 유지)
