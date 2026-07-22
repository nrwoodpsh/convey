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
    SCENARIO_READY = "scenario_ready"  # 시나리오 생성 완료·사람 승인 대기(수동 흐름, ㉓)
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


# ── 운영 대시보드(무인증, ADR 0010·0011) — 계약 api-contract-dashboard.py ──
class ArticleItem(BaseModel):
    """오늘자 수집 기사 1건(대시보드 선택 대상). research에서 회수."""

    article_id: int
    title: str
    source_url: str
    published_at: str  # ISO-8601 UTC
    ticker: str | None = None
    name: str | None = None  # 종목 한글명


class ArticleListRes(BaseModel):
    items: list[ArticleItem] = Field(default_factory=list)


class DashboardGenerateReq(BaseModel):
    """기사 선택 → 초안 생성(㉓). 제목=기사 제목, 종목=태깅 종목. 스크립트만·승인 대기."""

    title: str = Field(min_length=1, max_length=200)
    ticker: str | None = Field(default=None, max_length=20)
    article_id: int | None = None


class JobListItem(BaseModel):
    """대시보드 목록 1행 — 잡 요약. content_id 있으면 미리보기 가능."""

    job_id: int
    topic: str
    ticker: str | None = None
    name: str | None = None  # 종목 한글명(공유 사전). 사전 밖이면 None → FE는 코드 미표시
    status: str
    content_id: int | None = None
    created_at: str  # ISO-8601 UTC


class JobListRes(BaseModel):
    """이전 잡 목록 — 최신순(created_at desc)."""

    items: list[JobListItem] = Field(default_factory=list)


class ScriptSectionView(BaseModel):
    """시나리오 섹션 1개(미리보기용). 수치 슬롯은 사실값으로 채워 노출."""

    kind: str  # hook | chart | fact | macro | closing
    text: str


class ScriptCiteView(BaseModel):
    """근거 출처(알파1 — 무출처 금지)."""

    claim: str
    source_url: str


class ScriptView(BaseModel):
    """미리보기 시나리오 — 스크립트 섹션 + 출처. 없으면 sections 빈 목록."""

    sections: list[ScriptSectionView] = Field(default_factory=list)
    citations: list[ScriptCiteView] = Field(default_factory=list)
