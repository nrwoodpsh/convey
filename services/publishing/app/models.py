"""publishing 모델 — 발행 기록(멱등·재시도). 라운드⑤.

content_id를 **유니크 멱등 키**로 — 같은 콘텐츠는 한 번만 업로드(아웃박스 유실 시 중복 방지).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)  # 멱등 키
    channel: Mapped[str] = mapped_column(String(20), default="youtube")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
