"""
타입/설정 계약 — 확장 프로그램(연출·데이터·안정), C 제외 (라운드㉙, Phase D·E·F)
검증: python -m mypy --strict --ignore-missing-imports api-contract-expansion.py

C(배포·YouTube 자동·Supabase)는 제외. 구현은 Phase D→E→F 단계별 /run.
대부분 기존 배선 확대(DART·RSS·pykrx는 이미 연결됨) + 배경 컷 전환·재시도 신규.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# ══ Phase D — 연출(배경 컷/xfade 전환 + 수치 scale 팝) ══
# content가 media.assemble에 **여러 배경 검색어**를 실어 보내면 video-assembly가 N개 클립을
# xfade로 이어붙인다. 실패 시 단일 배경 폴백(현행). 수치는 chart 구간에 scale 바운스 팝.
MAX_BG_CLIPS = 3  # 배경 컷 최대 개수(렌더 시간·리스크 상한)


class MultiBrollNote(BaseModel):
    """media.assemble 확장 — broll_queries(복수). 없으면 기존 broll_query 단일(하위호환)."""

    broll_queries: list[str] = Field(default_factory=list)  # 예: [산업, 추상, 시장]


# ══ Phase E — 데이터(종목 마스터·수집 확대·백필) ══
# 종목 마스터: 오프라인 pykrx 스크립트가 common/stocks.py를 재생성(정적 커밋, 런타임 의존 X).
GEN_STOCKS_NOTE = "scripts/gen-stocks.py (pykrx) → libs/common/common/stocks.py 재생성(코스피200+)."
# 시세 확대: market-feed symbols를 마스터 상위 N개로. 뉴스: news-feed feed_urls 추가.
# DART: 이미 수집 중 → 공시를 그래프 **사건(HAS_EVENT)**으로 태깅해 활용 강화.
# 백필: 과거 articles에 LLM 관계추출까지(현행 백필=결정론 섹터엣지만) — 일회성 스크립트(Ollama).

# ══ Phase F — 안정(재시도·자동양산 검증·모니터링) ══
# 재시도: 합성/스크립트 **일시 실패**를 N회 재시도(지수 백오프). 영구 실패는 failed 유지.
RETRY_MAX = 2
RETRY_BACKOFF_SEC = (5.0, 20.0)  # 시도 간 대기


class UiStatsRes(BaseModel):
    """대시보드 모니터링(F) — 상태별 잡 수·최근 실패. GET /ui/stats(무인증, 로컬)."""

    by_status: dict[str, int] = Field(default_factory=dict)
    recent_failed: list[dict[str, str]] = Field(default_factory=list)  # {job_id, topic, error}


UI_STATS_ENDPOINT = ("GET", "/ui/stats")
