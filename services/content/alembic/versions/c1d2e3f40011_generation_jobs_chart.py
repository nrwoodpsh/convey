"""generation_jobs chart (승인 게이트용 차트 근거 보존, 라운드㉓)

Revision ID: c1d2e3f40011
Revises: 7598c32287dd
Create Date: 2026-07-22 16:40:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c1d2e3f40011'
down_revision: str | None = '7598c32287dd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 승인 대기(scenario_ready) 동안 차트 근거 보존 → 승인 시 media.assemble 재발행에 재사용
    op.add_column('generation_jobs', sa.Column('chart', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('generation_jobs', 'chart')
