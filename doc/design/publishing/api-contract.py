"""
API 계약 — 라운드 ⑤: publishing (발행·양산) · 알파4 · ADR 0003
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

content.approved 소비 → YouTube Shorts 업로드. **발행은 사람 승인 후에만**(가드레일).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

TOPIC_CONTENT_APPROVED = "content.approved"  # 구독 (사람 승인본)
TOPIC_CONTENT_PUBLISHED = "content.published"  # 발행 (관측)

PUBLISH_STATUS_ENDPOINT = ("GET", "/publishing/{content_id}")


class Channel(str, Enum):
    YOUTUBE = "youtube"


class PublishRequest(BaseModel):
    content_id: int
    channel: Channel = Channel.YOUTUBE
    title: str = Field(max_length=100)
    description: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)


class PublishStatus(str, Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishRes(BaseModel):
    content_id: int
    channel: Channel
    status: PublishStatus
    external_url: str | None = None
    error: str | None = None


class ContentPublishedEvent(BaseModel):
    content_id: int
    channel: Channel
    external_url: str
    published_at: datetime  # UTC


class PublishError(tuple[str, int, str], Enum):
    NOT_APPROVED = ("PUB001", 409, "승인되지 않은 콘텐츠입니다.")
    UPLOAD_FAILED = ("PUB002", 502, "외부 업로드에 실패했습니다.")
