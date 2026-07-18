from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # 에이전트는 모델을 직접 품지 않고 llm-inference(모델 서빙 서비스)를 호출한다.
    # 게이트웨이를 다시 타지 않고 east-west 직접 호출 + HMAC 서명(gateway_internal_secret 재사용).
    llm_inference_url: str = "http://llm-inference:8000"

    # 에이전트 루프 상한 — LLM 호출 횟수가 곧 비용이므로 반드시 상한을 둔다.
    max_steps: int = 5

    # RAG(선택) — 벡터DB 붙일 때 사용
    embedding_model: str = "nomic-embed-text"
    vector_top_k: int = 4


settings = Settings()
