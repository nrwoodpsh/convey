"""타입 계약 — admin 서비스(운영자 설정) + admin_db. 라운드㉝. ADR 0016.

검증: python -m mypy --strict --ignore-missing-imports api-contract-admin.py

목적: 수집·관심 설정을 운영자가 대시보드에서 관리. 종목 마스터를 코드(common.stocks)에서
admin_db로 승격(단일 진실). news-feed·issue-detector는 admin API로 설정을 읽는다(Database per Service).

수집 = 넓게(경제·주식·사회·정치). 관심/핫함 필터 = 코스피200(기본 ON) + 등록 키워드(체크박스).
가드레일: 자격증명(.env)·무출처 0·로컬 LLM만 불변. admin_db는 admin 서비스만 직접 접근.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

Period = Literal["1w", "1m", "3m"]  # 검색 기간
SourceName = Literal["naver", "rss", "dart"]


# ── admin_db 엔티티 ──
@dataclass
class Stock:
    """종목 마스터(코스피200 시드) + 관심 on/off. common.stocks 46 → 여기로 승격."""

    ticker: str          # PK 예: "005930"
    name: str            # "삼성전자"
    sector: str          # "반도체"(없으면 "")
    enabled: bool = True # watch on/off(기본 ON = 코스피200 baseline)


@dataclass
class Keyword:
    """운영자 등록 키워드(정치·사회·테마). 관심 필터의 추가 레이어."""

    id: int
    term: str
    enabled: bool = True


@dataclass
class SourceToggle:
    name: SourceName
    enabled: bool = True


@dataclass
class CollectionSettings:
    """수집 전역 설정(싱글턴)."""

    period: Period = "1w"


# ── GET /admin/config — 워커(news-feed·issue-detector)가 읽는 통합 설정 ──
@dataclass
class ConfigView:
    """활성(enabled)만 담아 워커에 제공. 워커는 이걸로 수집·필터·랭킹."""

    stocks: list[Stock] = field(default_factory=list)      # enabled=True인 종목
    keywords: list[str] = field(default_factory=list)      # enabled=True인 term
    sources: dict[str, bool] = field(default_factory=dict) # {"naver":T,"rss":T,"dart":T}
    period: Period = "1w"


# ── admin 서비스 HTTP API (게이트웨이 뒤 + 대시보드/워커가 호출) ──
class AdminApi(Protocol):
    """엔드포인트 계약. 읽기=워커·대시보드, 쓰기=대시보드(설정 메뉴)."""

    def get_config(self) -> ConfigView: ...                    # GET /admin/config
    def list_stocks(self) -> list[Stock]: ...                  # GET /admin/stocks
    def set_stock_enabled(self, ticker: str, enabled: bool) -> Stock: ...  # PUT /admin/stocks/{ticker}
    def add_keyword(self, term: str) -> Keyword: ...           # POST /admin/keywords
    def set_keyword_enabled(self, kid: int, enabled: bool) -> Keyword: ...  # PUT /admin/keywords/{id}
    def delete_keyword(self, kid: int) -> None: ...            # DELETE /admin/keywords/{id}
    def set_source(self, name: SourceName, enabled: bool) -> SourceToggle: ...  # PUT /admin/sources/{name}
    def set_period(self, period: Period) -> CollectionSettings: ...  # PUT /admin/settings/period


# ── 시드(seed) — 코스피200 종목 마스터 최초 적재 ──
class SeedStocks(Protocol):
    """stock_master 최초 시드. 교체 가능(pluggable).

    - "naver"(기본): finance.naver.com 코스피200 페이지 스크래핑 — **계정 불필요**(접근 확인됨).
    - "pykrx": KRX(KRX_ID/KRX_PW 필요) — 계정 활성 시 갱신·검증용 대안.
    - "static": 번들 정적 파일 — 최후 fallback.
    멱등(ticker upsert). 이름·섹터 파싱 실패분은 로그 후 스킵(무출처 0 불변).
    """

    def __call__(self, source: Literal["naver", "pykrx", "static"] = "naver") -> int: ...
