"""공통 설정 베이스 — 각 서비스가 상속해 확장한다."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """모든 서비스 공통 환경 설정. env로 주입(ConfigServer 대체)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"

    # 인증(JWT)
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_ttl_seconds: int = 7200
    refresh_ttl_seconds: int = 86400

    # 게이트웨이↔서비스 HMAC 신뢰
    gateway_internal_secret: str = "change-me-internal"

    # Kafka
    kafka_bootstrap: str = "kafka:9092"
