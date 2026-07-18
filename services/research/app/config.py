from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/research_db"

    # 발행: 소스 원문 수집 완료 → content/agent 구독
    topic_ingested: str = "research.ingested"

    # RAG 임베딩 (로컬 Ollama만 — 외부 텍스트 LLM 금지)
    embedding_model: str = "nomic-embed-text"
    embedding_url: str = "http://llm-inference:8000"  # /embeddings 위임 (TODO(/design))


settings = Settings()
