"""content 도메인 Pydantic 스키마 — 계약(api-contract.py)과 정합."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    ticker: str | None = None
    issue_ref: str | None = Field(default=None, description="issue-detector 랭킹 참조(선택)")


class JobStatus(str, Enum):
    PENDING = "pending"
    SCRIPTING = "scripting"
    MEDIA = "media"
    ASSEMBLING = "assembling"
    READY = "ready"
    APPROVED = "approved"
    FAILED = "failed"


class JobRes(BaseModel):
    job_id: int
    status: str
    script_id: int | None = None
    content_id: int | None = None
    error: str | None = None


class SearchHit(BaseModel):
    content_id: int
    text: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
