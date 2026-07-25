"""admin_db 스키마 — 운영자 설정 + 종목 마스터 (ADR 0016, 라운드㉝).

대시보드가 쓰고, 워커(news-feed·issue-detector)가 GET /admin/config로 읽는다.
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String
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


class ScenarioTemplate(Base):
    """대본 형식 템플릿(㊳) — agent 하드코딩 노브를 admin_db로 승격. 운영자 편집.

    구조·톤만 제어(알파①): 수치는 price/macro, 관계는 그래프 근거 — 템플릿이 사실을 만들지 않음.
    """

    __tablename__ = "scenario_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(200), default="")
    n_facts: Mapped[int] = mapped_column(Integer, default=3)          # 사용 사실 개수
    n_relations: Mapped[int] = mapped_column(Integer, default=2)      # 사용 그래프 관계 개수
    use_macro: Mapped[bool] = mapped_column(Boolean, default=True)    # 거시 문장 포함
    use_closing: Mapped[bool] = mapped_column(Boolean, default=False)  # 마무리 문장 포함
    hook_tone: Mapped[str] = mapped_column(String(100), default="담백한 분석 톤")  # 훅 톤
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class BackgroundAsset(Base):
    """영상 배경 자산 라이브러리(㊴) — 운영자 등록. video-assembly가 섹터/태그 매칭으로 선택.

    파일 본체는 공유 볼륨(대용량), admin_db엔 경로·태그·라이선스 메타만(가드레일: 출처 계승).
    """

    __tablename__ = "background_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)  # 섹터/무드 매칭 태그
    path: Mapped[str] = mapped_column(String(300))              # 공유 볼륨 경로
    kind: Mapped[str] = mapped_column(String(10), default="image")  # image | video
    license: Mapped[str] = mapped_column(String(200), default="")   # 출처·라이선스(가드레일)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
