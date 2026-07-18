"""content 도메인 ORM 모델.

TODO(/design): 엔티티·컬럼 확정. 초안 엔티티(분석 doc 기준):
  - GenerationJob : 파이프라인 실행 단위·단계 상태(스크립트→미디어→합성→승인)
  - Script        : 로컬 LLM 생성 스크립트(대본·자막)
  - Asset         : 미디어 조각(이미지·음성·영상클립)+생성 소스/라이선스 메타
  - Content       : 완성본(쇼츠 mp4·이미지)
  - ReviewStatus  : 사람 승인 상태
  - ContentEmbedding : pgvector — 콘텐츠 히스토리 RAG(분리 인덱스 결정)
아래는 구조 확인용 최소 자리표시 — /design에서 재정의한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO(/design): status(상태머신), owner_id, research_refs, script_id ...
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# TODO(/design): Script, Asset, Content, ReviewStatus, ContentEmbedding(pgvector) 정의
