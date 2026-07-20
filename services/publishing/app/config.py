from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/publishing_db"

    topic_approved: str = "content.approved"  # 구독(사람 승인본)
    topic_published: str = "content.published"  # 발행 완료(관측)
    consumer_group: str = "publishing"

    # YouTube OAuth 토큰은 .env로만(발행 승인 후에만 사용). 커밋 금지.
    youtube_token: str = ""


settings = Settings()
