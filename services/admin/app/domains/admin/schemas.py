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


class TemplateOut(BaseModel):
    """시나리오 템플릿(㊳) — content/agent가 대본 생성에 사용하는 구조 노브."""

    id: int
    name: str
    description: str
    n_facts: int
    n_relations: int
    use_macro: bool
    use_closing: bool
    hook_tone: str
    enabled: bool


class TemplateIn(BaseModel):
    """템플릿 생성·수정 입력 — 구조·톤만(수치·관계는 Evidence, 알파①)."""

    name: str
    description: str = ""
    n_facts: int = 3
    n_relations: int = 2
    use_macro: bool = True
    use_closing: bool = False
    hook_tone: str = "담백한 분석 톤"
    enabled: bool = True


class BackgroundOut(BaseModel):
    """배경 자산(㊴) — video-assembly가 섹터/태그 매칭으로 선택."""

    id: int
    name: str
    tags: list[str]
    path: str
    kind: str
    license: str
    enabled: bool


class BackgroundIn(BaseModel):
    """배경 자산 등록·수정 — 파일은 공유 볼륨, 여기엔 경로·태그·라이선스 메타만."""

    name: str
    tags: list[str] = []
    path: str
    kind: str = "image"  # image | video
    license: str = ""
    enabled: bool = True
