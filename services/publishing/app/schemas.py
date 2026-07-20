"""publishing 스키마 — 계약(api-contract.py)과 정합."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Channel(str, Enum):
    YOUTUBE = "youtube"


class PublishStatus(str, Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishRes(BaseModel):
    content_id: int
    channel: str
    status: str
    external_url: str | None = None
    error: str | None = None
