"""JWT 발급/검증 + 게이트웨이↔서비스 HMAC 신뢰헤더.

게이트웨이 중앙 인증 패턴:
- 게이트웨이가 JWT 검증 후, 하류 호출에 사용자 컨텍스트 헤더 + HMAC 서명을 부착.
- 서비스는 HMAC을 검증해 '게이트웨이 경유'만 신뢰(직접호출 차단).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

import jwt

# 하류로 전달되는 신뢰 헤더 이름
H_USER_ID = "X-User-Id"
H_USER_NAME = "X-User-Name"
H_USER_ROLES = "X-User-Roles"  # CSV
H_TIMESTAMP = "X-Gateway-Timestamp"
H_SIGNATURE = "X-Gateway-Signature"

_MAX_SKEW_SECONDS = 60


# ── JWT ──────────────────────────────────────────────────
def create_token(
    *, subject: str, secret: str, algorithm: str, ttl_seconds: int, extra: dict | None = None
) -> str:
    now = int(time.time())
    payload = {"sub": subject, "iat": now, "exp": now + ttl_seconds, **(extra or {})}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])


# ── HMAC 신뢰헤더 ─────────────────────────────────────────
@dataclass
class UserContext:
    user_id: str
    user_name: str = ""
    roles: str = ""  # CSV


def _canonical(ts: str, user_id: str, path: str) -> bytes:
    return f"{ts}|{user_id}|{path}".encode()


def sign_internal(
    *, secret: str, user_id: str, path: str, ts: str | None = None
) -> tuple[str, str]:
    """(timestamp, signature) 반환. 게이트웨이가 하류 호출 직전 호출."""
    ts = ts or str(int(time.time()))
    sig = hmac.new(secret.encode(), _canonical(ts, user_id, path), hashlib.sha256).hexdigest()
    return ts, sig


def verify_internal(*, secret: str, user_id: str, path: str, ts: str, signature: str) -> bool:
    """서비스가 수신 요청 검증. ±60s skew 허용."""
    try:
        if abs(int(time.time()) - int(ts)) > _MAX_SKEW_SECONDS:
            return False
    except ValueError:
        return False
    expected = hmac.new(secret.encode(), _canonical(ts, user_id, path), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
