"""background_asset — 영상 배경 자산 라이브러리(㊴)

Revision ID: 0003_background_asset
Revises: 0002_scenario_template
Create Date: 2026-07-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_background_asset"
down_revision: str | None = "0002_scenario_template"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "background_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("path", sa.String(length=300), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False, server_default="image"),
        sa.Column("license", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("background_asset")
