"""
API 계약 — 운영 대시보드 (content, 로컬 전용·무인증 호스트 포트) · ADR 0010
검증: python -m mypy --strict --ignore-missing-imports api-contract-dashboard.py

배경: CONVEY는 API 전용 BE였다(화면 = 쇼츠 영상뿐). 사람이 브라우저에서
  ① 생성 버튼 클릭 → 쇼츠 제작 시작  ② 결과(제목·미리보기) 확인  ③ 이전 것까지 목록
을 하도록 content 서비스가 **정적 대시보드 + 운영 API(/ui/*) + mp4 스트리밍**을
새 호스트 포트에 노출한다. 이 경로는 gateway·Supabase 인증을 거치지 않는다
(로컬 운영 콘솔, ADR 0010). 기존 /content/* (gateway·HMAC 보호)는 그대로 둔다.

이 계약은 기존 api-contract.py(GenerateReq·JobRes·JobStatus)를 **재사용·확장**한다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# 기존 계약 재사용 (동일 폴더 api-contract.py) — 여기선 대시보드 전용만 정의
# JobStatus·JobRes는 api-contract.py 정의를 그대로 쓴다.

# ── 대시보드 엔드포인트 (content 호스트 포트, 무인증) ──
# 워크플로우(㉓): 오늘자 기사 목록 → 선택 → 진행(초안) → 시나리오 제시 → 승인 → 쇼츠 생성.
DASHBOARD_INDEX = ("GET", "/")  # 정적 대시보드 셸(index.html)
UI_ARTICLES_ENDPOINT = ("GET", "/ui/articles")  # 오늘자 수집 기사 목록(선택 대상) ← research east-west
UI_GENERATE_ENDPOINT = ("POST", "/ui/generate")  # 기사 선택 → 초안 잡(스크립트만, 승인 대기)
UI_JOBS_ENDPOINT = ("GET", "/ui/jobs")  # 이전 잡 목록
UI_JOB_ENDPOINT = ("GET", "/ui/jobs/{job_id}")  # 상태 폴링 → JobRes 재사용
UI_JOB_SCRIPT_ENDPOINT = ("GET", "/ui/jobs/{job_id}/script")  # 시나리오 제시(승인 전)
UI_APPROVE_SCENARIO_ENDPOINT = ("POST", "/ui/jobs/{job_id}/approve-scenario")  # 승인 → 합성 시작
UI_VIDEO_ENDPOINT = ("GET", "/ui/contents/{content_id}/video")  # mp4 스트리밍(Range)
UI_SCRIPT_ENDPOINT = ("GET", "/ui/contents/{content_id}/script")  # 완성본 시나리오

# research (east-west, gateway·HMAC) — content가 대시보드용으로 호출. research가 구현.
RESEARCH_ARTICLES_ENDPOINT = ("GET", "/research/articles")  # 오늘자 수집 기사


class ArticleItem(BaseModel):
    """오늘자 수집 기사 1건 — 대시보드 선택 대상. 출처 필수(가드레일)."""

    article_id: int
    title: str
    source_url: str  # 가드레일: 무출처 금지
    published_at: str  # ISO-8601 UTC
    ticker: str | None = None  # 태깅된 대표 종목(있으면)
    name: str | None = None  # 종목 한글명(공유 사전)


class ArticleListRes(BaseModel):
    """오늘자 기사 목록 — 최신순."""

    items: list[ArticleItem] = Field(default_factory=list)


class DashboardGenerateReq(BaseModel):
    """기사 선택 → 초안 생성. 제목=기사 제목, 종목=태깅 종목. 초안(스크립트만, 승인 대기)."""

    title: str = Field(min_length=1, max_length=200, description="쇼츠 제목(기사 제목)")
    ticker: str | None = Field(default=None, max_length=20, description="종목코드")
    article_id: int | None = Field(default=None, description="근거 기사 id(선택 출처)")


class JobListItem(BaseModel):
    """대시보드 목록 1행 — 잡 요약. content_id 있으면 미리보기 가능."""

    job_id: int
    topic: str  # 제목(주제)
    ticker: str | None = None
    name: str | None = None  # 종목 한글명(공유 사전 common.stocks). 사전 밖이면 None
    status: str  # JobStatus 값(pending…ready/approved/failed)
    content_id: int | None = None  # 있으면 /ui/contents/{content_id}/video 재생 가능
    created_at: str  # ISO-8601 UTC (가드레일: UTC 저장·표기)


class JobListRes(BaseModel):
    """이전 잡 목록 — 최신순(created_at desc)."""

    items: list[JobListItem] = Field(default_factory=list)


class ScriptSectionView(BaseModel):
    """미리보기 시나리오 섹션 — 수치 슬롯은 사실값으로 채워 노출."""

    kind: str  # hook | chart | fact | macro | closing
    text: str


class ScriptCiteView(BaseModel):
    """근거 출처(알파1 — 무출처 금지)."""

    claim: str
    source_url: str


class ScriptView(BaseModel):
    """미리보기 시나리오 — 스크립트 섹션 + 출처. 스크립트 없으면 빈 목록."""

    sections: list[ScriptSectionView] = Field(default_factory=list)
    citations: list[ScriptCiteView] = Field(default_factory=list)


# ── 잡 상태(㉓ 신규) ──
# JobStatus에 SCENARIO_READY 추가: scripting → **scenario_ready(승인 대기)** → assembling → ready.
# 수동(대시보드)만 이 게이트를 거친다. 자동양산(issue.selected)은 scripting → assembling 직행(무정지).
JOB_STATUS_SCENARIO_READY = "scenario_ready"

# ── 에러 (기존 CNT 코드 재사용 + 대시보드 전용) ──
# CNT002 잡 없음 / CNT004 완성본(mp4)·완성본 없음 / CNT003 승인 불가 상태(scenario_ready 아님)
UI_CONTENT_NOT_FOUND = ("CNT004", 404, "완성본(mp4)을 찾을 수 없습니다.")
UI_SCENARIO_NOT_READY = ("CNT003", 409, "승인 가능한 상태가 아닙니다.")
