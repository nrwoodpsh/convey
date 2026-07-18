from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/content_db"

    # 구독: 생성 요청 (on-demand API 또는 research.ingested 자동)
    topic_generate: str = "content.generate"
    # 발행: 미디어 fan-out (후속 라운드)
    topic_image: str = "image.generate"
    topic_tts: str = "tts.generate"
    topic_video_clip: str = "video.clip"
    # 발행: 합성 완료 → 사람 승인 → publishing
    topic_ready: str = "content.ready"
    topic_approved: str = "content.approved"

    consumer_group: str = "content"

    # agent(스크립트 생성) east-west 호출
    agent_url: str = "http://agent:8000"

    # 콘텐츠 히스토리 RAG (분리 인덱스 — content_db pgvector)
    embedding_model: str = "nomic-embed-text"
    embedding_url: str = "http://llm-inference:8000"


settings = Settings()
