"""admin_db 스키마 — 운영자 설정 + 종목 마스터 (ADR 0016, 라운드㉝).

대시보드가 쓰고, 워커(news-feed·issue-detector)가 GET /admin/config로 읽는다.
"""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Stock(Base):
    """종목 마스터(코스피200 시드) + 관심 on/off. common.stocks 승격분."""

    __tablename__ = "stock"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sector: Mapped[str] = mapped_column(String(50), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 기본 ON(baseline)


class Keyword(Base):
    """운영자 등록 키워드(정치·사회·테마) — 관심 필터 추가 레이어."""

    __tablename__ = "keyword"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceToggle(Base):
    """수집처 on/off — naver·rss·dart."""

    __tablename__ = "source_toggle"

    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class CollectionSettings(Base):
    """수집 전역 설정(싱글턴 id=1) — 검색 기간."""

    __tablename__ = "collection_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(4), default="1w")  # 1w | 1m | 3m
