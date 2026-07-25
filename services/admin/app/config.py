from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/admin_db"
    # 시드 소스: "static"(common.stocks) | "naver"(코스피200 스크래핑, 후속) | "pykrx"
    seed_source: str = "static"


settings = Settings()
