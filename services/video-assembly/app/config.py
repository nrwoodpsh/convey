from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # content fan-out 완료 신호 구독(미디어 자산 준비되면 합성)
    topic_image: str = "image.generate"
    topic_tts: str = "tts.generate"
    consumer_group: str = "video-assembly"

    # 미디어 바이너리 저장 — POC는 로컬 볼륨(ADR 0006). 후속 MinIO/S3
    media_dir: str = "/data/media"


settings = Settings()
