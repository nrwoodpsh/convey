"""트랜잭션 아웃박스(㊱ P3) — content_db.outbox + publish_via_outbox 헬퍼.

직접 producer.publish 대신, 비즈니스 저장과 **같은 트랜잭션**에 봉투를 outbox 행으로 INSERT한다.
커밋되면 Debezium이 WAL에서 캐치해 토픽으로 발행(유실 0). 앱은 발행을 직접 하지 않는다.

payload 컬럼 = 봉투 전체(JSON) → 소비자의 이중경로 디코딩이 언랩해 도메인 payload만 넘긴다.
컬럼명은 Debezium Outbox Event Router 기본값(aggregatetype·aggregateid·type·payload).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from common.envelope import make_envelope
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # = event_id(UUID)
    aggregatetype: Mapped[str] = mapped_column(String(50))
    aggregateid: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(100))  # event_type=topic 라우팅
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)  # 봉투 JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def publish_via_outbox(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    producer: str,
    aggregate_type: str,
    aggregate_id: str,
    key: str | None = None,
) -> str:
    """봉투를 outbox 행으로 add(커밋은 호출자 트랜잭션). 반환=event_id. Debezium이 발행 담당."""
    env = make_envelope(event_type=event_type, payload=payload, producer=producer, key=key)
    session.add(
        Outbox(
            id=env.event_id,
            aggregatetype=aggregate_type,
            aggregateid=aggregate_id,
            type=event_type,
            payload=env.to_dict(),  # 봉투 전체(소비자가 언랩)
        )
    )
    return env.event_id
