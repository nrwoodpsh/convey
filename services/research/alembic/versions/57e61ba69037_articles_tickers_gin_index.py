"""articles tickers gin index

Revision ID: 57e61ba69037
Revises: bbba385fe7b9
Create Date: 2026-07-22 14:56:54.948442
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '57e61ba69037'
down_revision: str | None = 'bbba385fe7b9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # articles.tickers(JSONB) @> 컨테인먼트 조회 가속 (fact_search_by_ticker)
    op.create_index(
        "ix_articles_tickers", "articles", ["tickers"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_articles_tickers", table_name="articles")
