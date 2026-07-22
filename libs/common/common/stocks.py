"""종목 코드 ↔ 한글명 단일 소스 (POC 소규모 사전).

영상 렌더·대시보드·자동 양산 제목이 **같은 한글명**을 쓰도록 공유한다.
가드레일 아님(정보 정확성 편의) — 사전 밖 종목은 코드를 그대로 노출(환각 금지: 없는 이름 지어내지 않음).
전체 종목 마스터(pykrx/KRX 동기화)는 후속. 지금은 POC 주요 종목만.
"""
from __future__ import annotations

# ticker → 한글명
STOCK_NAMES: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "005380": "현대차",
    "373220": "LG에너지솔루션",
    "035420": "네이버",
    "035720": "카카오",
}


def stock_name(ticker: str | None) -> str | None:
    """코드 → 한글명. 사전 밖/없음이면 None(코드를 지어내지 않음)."""
    if not ticker:
        return None
    return STOCK_NAMES.get(ticker)


def stock_label(ticker: str | None) -> str:
    """표시용 라벨. 이름 있으면 '현대차(005380)', 없으면 코드 그대로, 코드도 없으면 빈 문자열."""
    if not ticker:
        return ""
    name = STOCK_NAMES.get(ticker)
    return f"{name}({ticker})" if name else ticker
