"""admin 설정 연동 순수 함수 검증(㉝ P3) — 검색어 도출·소스 토글."""
from __future__ import annotations

from app.admin_client import derive_queries, source_enabled


def test_derive_queries_stocks_and_keywords() -> None:
    cfg = {
        "stocks": [{"name": "삼성전자"}, {"name": "SK하이닉스"}],
        "keywords": ["AI반도체", "금리"],
    }
    assert derive_queries(cfg) == ["삼성전자", "SK하이닉스", "AI반도체", "금리"]


def test_derive_queries_dedup_and_empty() -> None:
    cfg = {"stocks": [{"name": "삼성전자"}], "keywords": ["삼성전자", "  "]}
    assert derive_queries(cfg) == ["삼성전자"]  # 중복·공백 제거


def test_source_enabled_default_on() -> None:
    assert source_enabled({}, "naver") is True  # 미설정은 기본 ON
    assert source_enabled({"sources": {"dart": False}}, "dart") is False
    assert source_enabled({"sources": {"dart": False}}, "rss") is True
