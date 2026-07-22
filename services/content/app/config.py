from __future__ import annotations

from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/content_db"

    # 구독: 생성 요청 (on-demand API 또는 research.ingested 자동)
    topic_generate: str = "content.generate"
    # 구독: 자동 양산(알파4) — issue-detector가 선별한 이슈 → 자동 잡 생성
    topic_issue_selected: str = "issue.selected"
    dedup_window_days: int = 1  # 자동 양산 중복회피 창(같은 종목 재생성 억제)
    narration_max_chars: int = 180  # 내레이션(음성) 문자 예산 — 쇼츠 길이(자막·인용은 전체 유지)
    # 오케스트레이션(키 없는 경로, 라운드⑤): content ↔ video-assembly
    topic_assemble: str = "media.assemble"  # 발행 → video-assembly
    topic_assembled: str = "content.assembled"  # 구독 ← video-assembly (fan-in)
    # 발행: 미디어 fan-out (외부 broll/TTS — 키 발급 후 라운드)
    topic_image: str = "image.generate"
    topic_tts: str = "tts.generate"
    topic_video_clip: str = "video.clip"
    # 발행: 합성 완료 → 사람 승인 → publishing
    topic_ready: str = "content.ready"
    topic_approved: str = "content.approved"

    consumer_group: str = "content"

    # agent(스크립트 생성) east-west 호출
    agent_url: str = "http://agent:8000"


settings = Settings()
