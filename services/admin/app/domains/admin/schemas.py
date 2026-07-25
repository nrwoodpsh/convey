from __future__ import annotations

from pydantic import BaseModel


class StockOut(BaseModel):
    ticker: str
    name: str
    sector: str
    enabled: bool


class StockToggle(BaseModel):
    enabled: bool


class KeywordOut(BaseModel):
    id: int
    term: str
    enabled: bool


class KeywordIn(BaseModel):
    term: str


class KeywordToggle(BaseModel):
    enabled: bool


class SourceIn(BaseModel):
    enabled: bool


class PeriodIn(BaseModel):
    period: str  # 1w | 1m | 3m


class ConfigView(BaseModel):
    """워커가 읽는 통합 설정 — 활성(enabled)만."""

    stocks: list[StockOut]
    keywords: list[str]
    sources: dict[str, bool]
    period: str
