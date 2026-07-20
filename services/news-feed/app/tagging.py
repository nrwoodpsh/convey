"""규칙/사전 기반 종목·사건 태깅 — 하이브리드 추출의 **결정론 절반**(환각 0). 라운드①.

관계추출(로컬 LLM)은 별개 단계. 여기선 사전에 있는 종목만 정확 매칭하고, 사건은
키워드 규칙으로 후보만 뽑는다. 사전에 없는 것은 만들어내지 않는다(무출처·환각 방지).
"""
from __future__ import annotations

# POC 종목 사전 (이름/별칭 → ticker). 운영에선 KRX 전체를 로드.
TICKER_DICT: dict[str, str] = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "현대차": "005380",
    "LG에너지솔루션": "373220",
    "네이버": "035420",
    "카카오": "035720",
}

# 사건 후보 키워드 (label → 트리거 단어들)
EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "실적": ("실적", "영업이익", "매출", "어닝"),
    "공시": ("공시", "자사주", "배당", "유상증자"),
    "급등락": ("급등", "급락", "상한가", "하한가"),
}


def tag_tickers(text: str, dictionary: dict[str, str] | None = None) -> list[str]:
    """본문에서 **사전에 있는 종목만** 태깅. 등장 순서 유지·중복 제거. 사전 밖은 태깅 안 함."""
    d = dictionary or TICKER_DICT
    tagged: list[str] = []
    for name, ticker in d.items():
        if name in text and ticker not in tagged:
            tagged.append(ticker)
    return tagged


def tag_entity_names(text: str, dictionary: dict[str, str] | None = None) -> list[str]:
    """본문에 등장하는 사전 엔티티 **이름** 목록(관계추출 allowed용). 사전 밖은 포함 안 함."""
    d = dictionary or TICKER_DICT
    return [name for name in d if name in text]


def tag_event_hints(text: str) -> list[str]:
    """사건 후보(실적·공시·급등락) 힌트 — 키워드 규칙. 확정이 아니라 후보."""
    hints: list[str] = []
    for label, keywords in EVENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hints.append(label)
    return hints
