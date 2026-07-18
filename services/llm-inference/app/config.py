from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"
    topic_train_jobs: str = "llm.train.jobs"


settings = Settings()
