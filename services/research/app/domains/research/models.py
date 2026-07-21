"""research 도메인 ORM 모델 — Postgres(사실)만. 관계·인과는 Neo4j(research_graph, ADR 0005).

계약: doc/design/research/api-contract.py (Article·PriceTick). 벡터 없음(ADR 0006).
가드레일: Article은 source_url·license 필수(무출처 금지).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000))  # 가드레일: 필수(NOT NULL)
    license: Mapped[str] = mapped_column(String(200))  # 가드레일: 필수(NOT NULL)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lang: Mapped[str] = mapped_column(String(8), default="ko")
    # 규칙 태깅된 종목 코드(라운드⑧) — 종목 기준 기사 회수. JSONB @> 컨테인먼트.
    tickers: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceTick(Base):
    __tablename__ = "price_ticks"
    # 멱등 저장: 같은 종목·거래일은 1행(장중 갱신). market-feed 반복 발행 중복 방지.
    __table_args__ = (UniqueConstraint("ticker", "ts", name="uq_price_ticks_ticker_ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)


class MacroIndicator(Base):
    """거시 지표(ECOS·FRED) — 사실. 그래프 미경유(Postgres). 라운드⑥ (ADR 0008).

    가드레일: source_url 필수(무출처 금지). 값은 API 실측 그대로(조작 0).
    멱등: 같은 (name, as_of, source)는 1행(반복 폴링 중복 방지).
    """

    __tablename__ = "macro_indicators"
    __table_args__ = (
        UniqueConstraint("name", "as_of", "source", name="uq_macro_name_asof_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40), default="")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(20))  # 'ECOS' | 'FRED'
    source_url: Mapped[str] = mapped_column(String(500))  # 가드레일: 필수
