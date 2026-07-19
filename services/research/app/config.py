from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/research_db"

    # 발행: 소스 원문 수집 완료 → issue-detector/content 구독
    topic_ingested: str = "research.ingested"

    # 지식 그래프 — 관계·인과(Neo4j). round①에서 드라이버 연결 (ADR 0005)
    # neo4j_url: str = "bolt://neo4j:7687"  # TODO(round① /builder)


settings = Settings()
