"""라운드0 인증 검증 — Supabase JWKS 시뮬레이션.

실제 Supabase 키 대신 자체 RSA 키로 토큰을 서명해, 검증기가 서명·aud·만료를 올바로
판정하는지 확인한다(AC1·AC2 근거). PyJWKClient(네트워크)는 주입으로 대체.
"""
from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from common.errors import AppError
from common.supabase_auth import SupabaseVerifier, claims_to_user


class _FakeSigningKey:
    def __init__(self, key: Any) -> None:
        self.key = key


class _FakeJWKS:
    """PyJWKClient 대체 — 항상 주어진 공개키를 반환."""

    def __init__(self, public_key: Any) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


@pytest.fixture
def keypair() -> tuple[RSAPrivateKey, Any]:
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return priv, priv.public_key()


def _token(priv: RSAPrivateKey, claims: dict[str, Any]) -> str:
    return jwt.encode(claims, priv, algorithm="RS256")


def _verifier(pub: Any) -> SupabaseVerifier:
    return SupabaseVerifier(_FakeJWKS(pub), audience="authenticated", algorithms=["RS256"])


def test_verify_ok_and_mapping(keypair: tuple[RSAPrivateKey, Any]) -> None:
    priv, pub = keypair
    tok = _token(priv, {
        "sub": "u-1", "aud": "authenticated", "exp": int(time.time()) + 60,
        "email": "a@b.com",
        "user_metadata": {"name": "홍길동"},
        "app_metadata": {"roles": ["user", "admin"]},
    })
    claims = _verifier(pub).verify(tok)
    assert claims["sub"] == "u-1"
    user = claims_to_user(claims)
    assert user.user_id == "u-1"
    assert user.user_name == "홍길동"
    assert user.roles == "user,admin"


def test_name_falls_back_to_email(keypair: tuple[RSAPrivateKey, Any]) -> None:
    priv, pub = keypair
    tok = _token(priv, {
        "sub": "u-2", "aud": "authenticated", "exp": int(time.time()) + 60,
        "email": "x@y.com", "role": "authenticated",
    })
    user = claims_to_user(_verifier(pub).verify(tok))
    assert user.user_name == "x@y.com"
    assert user.roles == "authenticated"


def test_wrong_audience_rejected(keypair: tuple[RSAPrivateKey, Any]) -> None:
    priv, pub = keypair
    tok = _token(priv, {"sub": "u", "aud": "other", "exp": int(time.time()) + 60})
    with pytest.raises(AppError) as exc:
        _verifier(pub).verify(tok)
    assert exc.value.status == 401
    assert exc.value.code == "AUTH004"  # 계약: WRONG_AUDIENCE


def test_expired_rejected(keypair: tuple[RSAPrivateKey, Any]) -> None:
    priv, pub = keypair
    tok = _token(priv, {"sub": "u", "aud": "authenticated", "exp": int(time.time()) - 10})
    with pytest.raises(AppError) as exc:
        _verifier(pub).verify(tok)
    assert exc.value.status == 401
    assert exc.value.code == "AUTH003"  # 계약: EXPIRED


def test_forged_signature_rejected(keypair: tuple[RSAPrivateKey, Any]) -> None:
    priv, pub = keypair
    attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tok = _token(attacker, {"sub": "u", "aud": "authenticated", "exp": int(time.time()) + 60})
    with pytest.raises(AppError) as exc:
        _verifier(pub).verify(tok)  # pub은 attacker 키와 불일치 → 서명 실패
    assert exc.value.status == 401
    assert exc.value.code == "AUTH002"  # 계약: INVALID_TOKEN
