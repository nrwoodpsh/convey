"""
API 계약 — 라운드 ③: content + agent (근거 스크립트) · 알파1 · ADR 0004·0006
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

content = 제작 잡·스크립트·자산·완성본 소유. agent = research/content `/search` 근거 회수로
출처·수치가 인용된 스크립트 생성. 스크립트 = **템플릿 + 사실 슬롯**(환각 물리 차단) + 연결 문장.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# ── content 잡 엔드포인트 ──
GENERATE_ENDPOINT = ("POST", "/content/generate")
JOB_ENDPOINT = ("GET", "/content/jobs/{job_id}")
APPROVE_ENDPOINT = ("POST", "/content/{content_id}/approve")


class GenerateReq(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    ticker: str | None = None
    issue_ref: str | None = Field(default=None, description="issue-detector 랭킹 참조(선택)")


class JobStatus(str, Enum):
    PENDING = "pending"
    SCRIPTING = "scripting"  # agent 스크립트 생성 중
    MEDIA = "media"  # 미디어 fan-out (라운드④)
    ASSEMBLING = "assembling"  # video-assembly (라운드④)
    READY = "ready"  # 합성 완료(내부 상태) → 사람 승인 대기
    APPROVED = "approved"
    FAILED = "failed"


class JobRes(BaseModel):
    job_id: int
    status: JobStatus
    script_id: int | None = None
    content_id: int | None = None
    error: str | None = None


# ── 스크립트 (인용 근거 필수 — 알파1) ──
class Citation(BaseModel):
    claim: str  # 스크립트 내 수치·주장
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int  # Article/PriceTick id


class ScriptSection(BaseModel):
    kind: str  # 'hook' | 'fact' | 'chart' | 'closing'
    text: str  # 자막·내레이션(연결 문장)
    data_slots: dict[str, str] = Field(
        default_factory=dict, description="정확 수치 슬롯(종가·등락률 등) — 사실에서 채움"
    )


class Script(BaseModel):
    id: int
    job_id: int
    sections: list[ScriptSection] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)  # 모든 수치가 결속


# ── 이벤트 ──
TOPIC_CONTENT_GENERATE = "content.generate"  # content 자기 큐 → consumer
TOPIC_CONTENT_APPROVED = "content.approved"  # 사람 승인 → publishing


class ContentGenerateEvent(BaseModel):
    job_id: int
    topic: str
    ticker: str | None = None


# ── 에러 ──
class ContentError(tuple[str, int, str], Enum):
    INVALID_PARAM = ("CNT001", 400, "요청 파라미터가 유효하지 않습니다.")
    JOB_NOT_FOUND = ("CNT002", 404, "잡을 찾을 수 없습니다.")
    NOT_READY = ("CNT003", 409, "승인 가능한 상태가 아닙니다.")
