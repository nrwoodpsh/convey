"""content 도메인 ORM 모델 — 생성 잡 상태머신. 라운드③.

상태: pending→scripting→media→assembling→ready→approved(또는 failed). 계약: api-contract.py JobStatus.
Script·Asset·Content는 후속(잡이 참조만 — script_id·content_id).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
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

# TODO(후속): Script(인용 근거), Asset(미디어 메타), Content(완성본), ReviewStatus
