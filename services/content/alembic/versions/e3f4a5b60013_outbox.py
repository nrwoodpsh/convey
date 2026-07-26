"""outbox — 트랜잭션 아웃박스(㊱ P3, Debezium CDC). content_db.

Debezium Outbox Event Router 기본 컬럼명(aggregatetype·aggregateid·type·payload)에 맞춘다.
발행부가 비즈니스 저장과 **같은 트랜잭션**에 INSERT → Debezium이 WAL 캐치해 토픽으로 발행(유실 0).

Revision ID: e3f4a5b60013
Revises: d2e3f4a50012
Create Date: 2026-07-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3f4a5b60013"
down_revision: str | None = "d2e3f4a50012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", sa.String(length=36), nullable=False),          # = event_id(UUID)
        sa.Column("aggregatetype", sa.String(length=50), nullable=False),  # 예: content
        sa.Column("aggregateid", sa.String(length=64), nullable=False),    # 예: job_id
        sa.Column("type", sa.String(length=100), nullable=False),          # event_type=topic 라우팅
        sa.Column("payload", postgresql.JSONB(), nullable=False),          # 봉투 JSON(소비자가 언랩)
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("outbox")
