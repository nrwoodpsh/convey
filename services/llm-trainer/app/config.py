from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    topic_train_jobs: str = "llm.train.jobs"
    consumer_group: str = "llm-trainer"
    adapters_dir: str = "/app/adapters"


settings = Settings()
