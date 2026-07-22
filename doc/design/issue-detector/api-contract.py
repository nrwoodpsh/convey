"""
API 계약 — 라운드 ②: issue-detector (이슈 종목 선별) · 알파2 · ADR 0004
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

issue-detector = **워커 + 얇은 조회 API**. `market.ticks`·`research.ingested` 스트림을
자체 집계해 "오늘의 이슈 종목" 랭킹을 만들고, `GET /issues/today`로 노출한다.
(랭킹은 이벤트가 아니라 **조회 상태** — 아키텍처 정합)
DB 경계 유지: research/content DB 직접접속 없이 Kafka 스트림만 소비.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# 구독 토픽 (research 계약의 이벤트를 소비)
SUB_TOPICS = ("market.ticks", "research.ingested")

# 조회 API
ISSUES_TODAY_ENDPOINT = ("GET", "/issues/today")


class IssuesTodayReq(BaseModel):
    top_k: int = Field(default=10, ge=1, le=50)
    window_hours: int = Field(default=24, ge=1, le=168)


class IssueRankItem(BaseModel):
    ticker: str
    name: str = ""
    score: float  # 종합 점수
    price_change_pct: float  # 등락률(%)
    volume_z: float  # 거래량 z-score
    news_count: int  # 윈도우 내 뉴스 빈도
    rank: int = Field(ge=1)


class IssuesTodayRes(BaseModel):
    as_of: datetime  # UTC
    window_hours: int
    items: list[IssueRankItem] = Field(default_factory=list)


# 랭킹 가중치(기본) — score = w_change*|change| + w_volume*volume_z + w_news*news_count
class RankWeights(BaseModel):
    w_change: float = 0.5
    w_volume: float = 0.3
    w_news: float = 0.2


# 자동 양산(알파4, 라운드⑬) — 상위 이슈를 생성 트리거로 발행.
# 조회 상태(GET /issues/today)는 그대로 유지하고, "선별된 이슈"만 이벤트로 추가 발행한다.
TOPIC_ISSUE_SELECTED = "issue.selected"  # issue-detector 발행 → content 소비(자동 잡 생성)


class IssueSelectedEvent(BaseModel):
    ticker: str
    name: str = ""  # 종목명(스크립트 topic·검색용)
    score: float
    as_of: datetime  # UTC


class IssueError(tuple[str, int, str], Enum):
    INVALID_PARAM = ("ISS001", 400, "요청 파라미터가 유효하지 않습니다.")
