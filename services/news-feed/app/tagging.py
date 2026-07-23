"""규칙/사전 기반 종목·사건 태깅 — 하이브리드 추출의 **결정론 절반**(환각 0). 라운드①.

관계추출(로컬 LLM)은 별개 단계. 여기선 사전에 있는 종목만 정확 매칭하고, 사건은
키워드 규칙으로 후보만 뽑는다. 사전에 없는 것은 만들어내지 않는다(무출처·환각 방지).
"""
from __future__ import annotations

from common.stocks import ENTITY_NAMES, STOCK_NAMES

# POC 종목 사전 (이름 → ticker) — 공유 소스(common.stocks) 확대분(㉕/A3). 운영에선 KRX 전체.
TICKER_DICT: dict[str, str] = {name: ticker for ticker, name in STOCK_NAMES.items()}

# 사건 후보 키워드 (label → 트리거 단어들)
EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "실적": ("실적", "영업이익", "매출", "어닝"),
    "공시": ("공시", "자사주", "배당", "유상증자"),
    "급등락": ("급등", "급락", "상한가", "하한가"),
}


def _suppress_substrings(names: list[str]) -> list[str]:
    """부분 문자열 이름 제거(㉙/E2) — 'SK'가 'SK하이닉스'에 포함되면 짧은 쪽 제거(오탐 방지)."""
    return [n for n in names if not any(n != m and n in m for m in names)]


def tag_tickers(text: str, dictionary: dict[str, str] | None = None) -> list[str]:
    """본문에서 **사전에 있는 종목만** 태깅. 등장 순서 유지·중복 제거. 사전 밖은 태깅 안 함."""
    d = dictionary or TICKER_DICT
    matched = _suppress_substrings([name for name in d if name in text])
    tagged: list[str] = []
    for name in matched:
        if d[name] not in tagged:
            tagged.append(d[name])
    return tagged


def tag_entity_names(text: str, names: tuple[str, ...] | None = None) -> list[str]:
    """본문에 등장하는 사전 엔티티 **이름** 목록(관계추출 allowed용) — 종목 + 섹터(㉕/A3).

    사전 밖은 포함 안 함(환각 방지). 짧은 부분 문자열 이름은 긴 이름에 포함되면 제거(㉙/E2).
    """
    allow = names or ENTITY_NAMES
    return _suppress_substrings([name for name in allow if name in text])


def tag_event_hints(text: str) -> list[str]:
    """사건 후보(실적·공시·급등락) 힌트 — 키워드 규칙. 확정이 아니라 후보."""
    hints: list[str] = []
    for label, keywords in EVENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hints.append(label)
    return hints
