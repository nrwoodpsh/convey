"""research 도메인 ORM 모델.

이 파일은 Postgres(사실) 저장만 담당한다. 관계·인과는 Neo4j(research_graph)에 별도 저장(ADR 0005).
TODO(/design): 엔티티·컬럼 확정. 초안 엔티티(분석 doc 기준):
  - Source      : 리서치 소스 정의(RSS 피드 URL·외부 API 엔드포인트)
  - Article     : 수집 원문 + 출처 URL·라이선스 메타(가드레일: 필수 동반) + 발행일
  - PriceTick   : 시세 시계열(차트·이슈감지용) — ticker·date 인덱스
  - Ingestion   : 수집 실행 이력
아래는 구조 확인용 최소 자리표시 — /design에서 재정의한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO(/design): source_id FK, title, body, source_url(필수), license(필수), published, lang ...
    source_url: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# TODO(/design): Source, PriceTick, Ingestion 정의 (관계·인과는 Neo4j research_graph)
