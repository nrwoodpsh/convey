from __future__ import annotations

import json
from typing import Any

from common.config import BaseAppSettings

# 거시 지표 기본 집합(코드는 config로 — 하드코딩 회피, ADR 0008 결정4)
_DEFAULT_ECOS = [
    {"name": "한국은행 기준금리", "stat_code": "722Y001", "cycle": "M", "item_code": "0101000", "unit": "연%"},
    {"name": "원달러환율(매매기준율)", "stat_code": "731Y003", "cycle": "D", "item_code": "0000003", "unit": "원"},
    {"name": "소비자물가지수", "stat_code": "901Y009", "cycle": "M", "item_code": "0", "unit": "2020=100"},
]
_DEFAULT_FRED = [
    {"name": "연방기금금리(실효)", "series_id": "DFF", "unit": "%"},
    {"name": "미 소비자물가지수", "series_id": "CPIAUCSL", "unit": "1982-84=100"},
]


class Settings(BaseAppSettings):
    # 발행: 수집 원문 → research/issue-detector 구독
    topic_ingested: str = "research.ingested"
    topic_macro: str = "research.macro"  # 거시 사실 → research(MacroIndicator)

    poll_interval_seconds: float = 300.0  # 뉴스·공시 폴링 주기
    macro_poll_interval_seconds: float = 86400.0  # 거시 폴링(저빈도 — 일 1회)

    # 소스 (ADR 0008): 무료
    feed_urls: str = "https://www.yna.co.kr/rss/economy.xml,https://www.hankyung.com/feed/economy"
    dart_api_key: str = ""  # opendart.fss.or.kr (무료). 없으면 공시 스킵
    naver_client_id: str = ""  # developers.naver.com 검색 API (무료). 없으면 뉴스검색 스킵
    naver_client_secret: str = ""
    ecos_api_key: str = ""  # ecos.bok.or.kr (무료). 없으면 국내 거시 스킵
    fred_api_key: str = ""  # fred.stlouisfed.org (무료). 없으면 미 거시 스킵

    # 거시 지표 집합(JSON 문자열로 오버라이드 가능 — 비우면 기본값)
    ecos_indicators_json: str = ""
    fred_indicators_json: str = ""

    @property
    def ecos_indicators(self) -> list[dict[str, Any]]:
        return json.loads(self.ecos_indicators_json) if self.ecos_indicators_json else _DEFAULT_ECOS

    @property
    def fred_indicators(self) -> list[dict[str, Any]]:
        return json.loads(self.fred_indicators_json) if self.fred_indicators_json else _DEFAULT_FRED


settings = Settings()
