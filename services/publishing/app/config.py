from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/publishing_db"

    topic_approved: str = "content.approved"  # 구독(사람 승인본)
    topic_published: str = "content.published"  # 발행 완료(관측)
    consumer_group: str = "publishing"

    # 완성 mp4 공유 볼륨(video-assembly와 공유) — 이벤트 mp4_path 없을 때 폴백 경로.
    media_dir: str = "/data/media"

    # YouTube OAuth2 자격증명은 .env로만(발행 승인 후에만 사용). 커밋 금지(.env.example엔 이름만).
    # 셋 다 있어야 업로드 시도, 하나라도 비면 skip(미연결로 기록 — 파이프라인 보호).
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""
    youtube_privacy: str = "private"  # 기본 비공개(가드레일 — 운영자가 수동 공개)
    youtube_token_uri: str = "https://oauth2.googleapis.com/token"


settings = Settings()
