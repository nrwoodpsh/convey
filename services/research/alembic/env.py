"""Alembic 비동기 마이그레이션 환경."""
from __future__ import annotations

import asyncio

import app.domains.research.models  # noqa: F401 — 메타데이터 등록 (도메인 추가 시 여기에 import)
from alembic import context
from app.config import settings
from app.db import Base
from sqlalchemy.ext.asyncio import create_async_engine

target_metadata = Base.metadata


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
