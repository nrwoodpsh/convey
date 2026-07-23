"""종목 코드 ↔ 한글명 단일 소스 (POC 소규모 사전).

영상 렌더·대시보드·자동 양산 제목이 **같은 한글명**을 쓰도록 공유한다.
가드레일 아님(정보 정확성 편의) — 사전 밖 종목은 코드를 그대로 노출(환각 금지: 없는 이름 지어내지 않음).
전체 종목 마스터(pykrx/KRX 동기화)는 후속. 지금은 POC 주요 종목만.
"""
from __future__ import annotations

# ticker → 한글명 (POC 주요 종목 — 확대, ㉕/A3). 전체 마스터(pykrx)는 후속.
STOCK_NAMES: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "005380": "현대차",
    "000270": "기아",
    "373220": "LG에너지솔루션",
    "006400": "삼성SDI",
    "051910": "LG화학",
    "035420": "네이버",
    "035720": "카카오",
    "005490": "POSCO홀딩스",
    "105560": "KB금융",
    "055550": "신한지주",
    "005935": "삼성전자우",
    "000810": "삼성화재",
    "207940": "삼성바이오로직스",
    "068270": "셀트리온",
    "028260": "삼성물산",
    "012330": "현대모비스",
    "066570": "LG전자",
    "003670": "포스코퓨처엠",
}

# 종목 한글명 → 대표 섹터. 단일 종목 기사도 종목–섹터 그래프 엣지(BELONGS_TO)를 만들기 위함(㉕/A3).
STOCK_SECTOR: dict[str, str] = {
    "삼성전자": "반도체", "SK하이닉스": "반도체", "삼성전자우": "반도체",
    "현대차": "자동차", "기아": "자동차", "현대모비스": "자동차",
    "LG에너지솔루션": "2차전지", "삼성SDI": "2차전지", "LG화학": "2차전지", "포스코퓨처엠": "2차전지",
    "네이버": "인터넷", "카카오": "인터넷",
    "POSCO홀딩스": "철강", "KB금융": "금융", "신한지주": "금융", "삼성화재": "금융",
    "삼성바이오로직스": "바이오", "셀트리온": "바이오",
    "삼성물산": "지주·건설", "LG전자": "가전",
}

# 관계추출 허용 엔티티 후보 = 종목명 + 섹터(사전 밖은 인식 안 함 — 환각 방지).
SECTORS: tuple[str, ...] = tuple(dict.fromkeys(STOCK_SECTOR.values()))
ENTITY_NAMES: tuple[str, ...] = (*STOCK_NAMES.values(), *SECTORS)


def stock_name(ticker: str | None) -> str | None:
    """코드 → 한글명. 사전 밖/없음이면 None(코드를 지어내지 않음)."""
    if not ticker:
        return None
    return STOCK_NAMES.get(ticker)


def sector_of(name: str | None) -> str | None:
    """종목 한글명 → 섹터. 없으면 None."""
    if not name:
        return None
    return STOCK_SECTOR.get(name)


def stock_label(ticker: str | None) -> str:
    """표시용 라벨. 이름 있으면 '현대차(005380)', 없으면 코드 그대로, 코드도 없으면 빈 문자열."""
    if not ticker:
        return ""
    name = STOCK_NAMES.get(ticker)
    return f"{name}({ticker})" if name else ticker
