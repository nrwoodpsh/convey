"""admin init — stock·keyword·source_toggle·collection_settings (㉝ P1)

Revision ID: 0001_admin_init
Revises:
Create Date: 2026-07-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_admin_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock",
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sector", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("ticker"),
    )
    op.create_table(
        "keyword",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("term"),
    )
    op.create_table(
        "source_toggle",
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "collection_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=4), nullable=False, server_default="1w"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("collection_settings")
    op.drop_table("source_toggle")
    op.drop_table("keyword")
    op.drop_table("stock")
