from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # 오케스트레이션(키 없는 경로, 라운드⑤): content → video-assembly → content
    topic_assemble: str = "media.assemble"  # 구독 ← content
    topic_assembled: str = "content.assembled"  # 발행 → content(fan-in)
    consumer_group: str = "video-assembly"

    # 외부 broll/TTS fan-out(키 발급 후 라운드)
    topic_image: str = "image.generate"
    topic_tts: str = "tts.generate"

    # 미디어 바이너리 저장 — POC는 로컬 볼륨(ADR 0006). 후속 MinIO/S3
    media_dir: str = "/data/media"


settings = Settings()
