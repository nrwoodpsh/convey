"""content 도메인 ORM 모델 — 생성 잡 상태머신. 라운드③.

상태: pending→scripting→media→assembling→ready→approved(또는 failed). 계약: api-contract.py JobStatus.
Script·Asset·Content는 후속(잡이 참조만 — script_id·content_id).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # JobStatus 값
    topic: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(64))
    script_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class Script(Base):
    """근거 스크립트 — agent 산출. 수치는 사실 슬롯, 모든 항목 인용 결속(알파1). 라운드⑤."""

    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # {kind,text,data_slots}
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # {claim,source_url,ref_id}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Content(Base):
    """완성본 메타 — mp4 경로(로컬 볼륨, ADR 0006). 바이너리는 볼륨에, DB엔 경로·메타만."""

    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)
    mp4_path: Mapped[str] = mapped_column(String(500))
    # broll 배경 자산 출처·라이선스(가드레일: 미디어 자산 출처 계승, 라운드⑫). 폴백 시 NULL
    broll_source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    broll_author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    broll_license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# TODO(후속): TTS 자산 메타, ReviewStatus
