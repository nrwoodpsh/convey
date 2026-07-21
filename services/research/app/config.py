from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/research_db"

    # 발행: 소스 원문 수집 완료 → issue-detector/content 구독
    topic_ingested: str = "research.ingested"
    # 시세 스트림(market-feed pykrx) → PriceTick 사실 저장
    topic_ticks: str = "market.ticks"
    # 거시 스트림(news-feed ECOS·FRED) → MacroIndicator 사실 저장
    topic_macro: str = "research.macro"

    # 지식 그래프 — 관계·인과(Neo4j, ADR 0005)
    neo4j_url: str = "bolt://neo4j:7687"
    neo4j_auth: str = "neo4j/convey-dev-pw"  # "user/pass" (NEO4J_AUTH env)

    # 관계추출 LLM — 로컬 Ollama 경유(llm-inference). 가드레일: 외부 텍스트 LLM 금지
    llm_inference_url: str = "http://llm-inference:8000"
    consumer_group: str = "research"


settings = Settings()
