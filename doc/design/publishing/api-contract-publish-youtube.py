"""타입 계약 — M4: YouTube 자동 발행(C1) + Supabase 인증 활성화(C2). 라운드㊶. ADR 0007·0010.

검증: python -m mypy --strict --ignore-missing-imports api-contract-publish-youtube.py

배경: 완성본까지 전자동, 발행은 미구현(publishing/youtube.py 스텁). 인증도 게이트웨이 JWKS 코드만 있고
미활성(C2). M4 = ①YouTube OAuth 실연결(승인 게이트 후) ②Supabase 실연결 + 대시보드 게이트웨이 뒤로.
가드레일: **콘텐츠 자동 발행 금지 — 사람 승인 후에만**(content.approved). 외부 키는 .env(커밋 금지).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

PublishStatus = Literal["pending", "uploading", "published", "failed"]


@dataclass
class PublishRecord:
    """발행 기록(publishing_db) — 멱등·재시도. 이미 있는 스키마 확장."""

    job_id: int
    content_id: int
    status: PublishStatus
    youtube_id: str = ""     # 업로드 성공 시 영상 id
    error: str = ""


@dataclass
class UploadMeta:
    """YouTube 업로드 메타 — 제목·설명(출처 포함)·태그·공개범위."""

    title: str
    description: str          # 출처·면책 포함(알파① 근거 계승)
    tags: list[str]
    privacy: Literal["private", "unlisted", "public"] = "private"  # 기본 비공개(안전)


# ── C1. YouTube 발행 (승인 후에만) ──
class YouTubePublisher(Protocol):
    """content.approved(사람 승인) 소비 → mp4 업로드. OAuth 토큰은 .env. 스텁 → 실연결.

    가드레일: 승인 이벤트가 있어야만 호출(자동 발행 금지). 실패 시 재시도·기록.
    """

    def upload(self, mp4_path: str, meta: UploadMeta) -> PublishRecord: ...


# ── C2. Supabase 인증 활성화 (코드는 구현됨 — 게이트웨이 JWKS) ──
# 남은 일: Supabase 프로젝트 생성 + .env(SUPABASE_URL·JWKS_URL·AUD) 채움(이미 값 있음 — 실프로젝트 검증).
#          대시보드(:8091 무인증)를 게이트웨이 뒤로 이동 or 인증 추가(ADR 0010 후속).
AUTH_ACTIVATION_NOTE = (
    "게이트웨이 JWKS 검증 코드 완비(ADR 0007). 활성화 = Supabase 실프로젝트 + 대시보드 노출 정리. "
    "대시보드는 게이트웨이 뒤로(인증) 또는 로컬 전용 유지 결정."
)

PUBLISH_GUARDRAIL = (
    "content.approved(사람 승인) 후에만 업로드. 기본 privacy=private. 출처·면책 description 계승. "
    "OAuth·API 키는 .env(커밋 금지, .env.example엔 키 이름만)."
)
