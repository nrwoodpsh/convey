"""research 도메인 ORM 모델.

TODO(/design): 엔티티·컬럼 확정. 초안 엔티티(분석 doc 기준):
  - Source      : 리서치 소스 정의(RSS 피드 URL·외부 API 엔드포인트)
  - Document    : 수집 원문 + 출처 URL·라이선스 메타(가드레일: 필수 동반)
  - Ingestion   : 수집 실행 이력
  - Embedding   : pgvector 벡터(원문 임베딩) — Vector 컬럼은 pgvector.sqlalchemy.Vector 사용
아래는 구조 확인용 최소 자리표시 — /design에서 재정의한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO(/design): source_id FK, title, body, source_url(필수), license(필수), lang ...
    source_url: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# TODO(/design): Source, Ingestion, Embedding(pgvector Vector 컬럼) 정의
