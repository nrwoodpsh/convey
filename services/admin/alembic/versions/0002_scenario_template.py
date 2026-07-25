"""scenario_template — 대본 형식 템플릿(㊳)

Revision ID: 0002_scenario_template
Revises: 0001_admin_init
Create Date: 2026-07-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_scenario_template"
down_revision: str | None = "0001_admin_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("n_facts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("n_relations", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("use_macro", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("use_closing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hook_tone", sa.String(length=100), nullable=False,
                  server_default="담백한 분석 톤"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("scenario_template")
