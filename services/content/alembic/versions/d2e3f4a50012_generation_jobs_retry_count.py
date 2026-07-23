"""generation_jobs retry_count (합성 재시도, 라운드㉙/F1)

Revision ID: d2e3f4a50012
Revises: c1d2e3f40011
Create Date: 2026-07-23 09:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd2e3f4a50012'
down_revision: str | None = 'c1d2e3f40011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'generation_jobs',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('generation_jobs', 'retry_count')
