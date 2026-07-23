"""미디어 오케스트레이션 공용 헬퍼(라운드㉓) — 내레이션·broll 검색어·assemble 이벤트 구성.

consumer(자동/수동 스크립트)와 service(승인 후 합성)가 **동일한 assemble 이벤트**를 만들도록
순수 함수로 분리(순환 import 방지: consumer→service, service→media, consumer→media).
"""
from __future__ import annotations

from typing import Any

# broll 배경 검색어 — 종목→영문 섹터 키워드(라운드⑯·㉒). 알려진 종목=대표 산업, 미지=우주의 불빛.
_BROLL_MAP: dict[str, str] = {
    "005930": "microchip circuit macro",     # 삼성전자 — 반도체
    "000660": "semiconductor wafer",         # SK하이닉스 — 반도체
    "035420": "data center servers",         # 네이버 — 데이터센터/인터넷
    "035720": "digital network city",        # 카카오 — 디지털/모바일
    "005380": "car factory assembly line",   # 현대차 — 자동차 공장
    "373220": "ev battery manufacturing",    # LG에너지솔루션 — 배터리
}
_BROLL_DEFAULT = "galaxy space stars glowing"  # 우주의 불빛(범용 프리미엄)
_BROLL_ANIM = "abstract motion graphics loop"  # 애니메이션 배경(㉔) — Pexels 모션그래픽·추상


def broll_query(ticker: str | None, background: str = "real") -> str:
    """배경 검색어(㉔). background=anim → 모션그래픽·추상. real → 종목 산업(미지=우주의 불빛)."""
    if background == "anim":
        return _BROLL_ANIM
    return _BROLL_MAP.get(ticker or "", _BROLL_DEFAULT)


def clip(text: str, max_chars: int) -> str:
    """문자 예산 초과 시 문장/단어 경계에서 컷(음성이 중간에 안 끊기게)."""
    if len(text) <= max_chars:
        return text
    head = text[:max_chars]
    dot = max(head.rfind(". "), head.rfind("! "), head.rfind("? "), head.rfind("다. "))
    if dot > 0:
        return head[: dot + 1].strip()
    space = head.rfind(" ")
    return (head[:space] if space > 0 else head).strip()


def build_narration(sections: list[dict[str, Any]], max_chars: int) -> str:
    """내레이션(음성 낭독용) — 핵심 섹션만 축약(hook + chart 1 + 사실 1 + 거시 1), 문자 예산.

    자막·인용(Script)은 전체 유지, 음성만 간결(쇼츠 길이). chart 슬롯은 사실값 해소.
    """
    parts: list[str] = []
    # relation(그래프 인과) 포함 — 알파가 음성에도 들리게(㉕). 순서: 훅→수치→인과→사실→거시.
    for kind in ("hook", "chart", "relation", "fact", "macro"):
        sec = next((s for s in sections if s.get("kind") == kind), None)
        if sec is None:
            continue
        text = str(sec.get("text", ""))
        slots = sec.get("data_slots") or {}
        if kind == "chart" and slots:
            try:
                text = text.format(**slots)
            except (KeyError, IndexError, ValueError):
                pass
        if text.strip():
            parts.append(text.strip())
    return clip(" ".join(parts), max_chars)


def build_assemble_event(
    *,
    job_id: int,
    topic: str,
    ticker: str | None,
    chart: dict[str, Any],
    sections: list[dict[str, Any]],
    narration_max_chars: int,
    background: str = "real",
) -> dict[str, Any]:
    """media.assemble 이벤트 구성 — 자동/승인 경로 공용. hook=자막, narration=음성, 배경=real|anim."""
    hook = next((s["text"] for s in sections if s.get("kind") == "hook"), topic)
    return {
        "job_id": job_id,
        "chart": chart,
        "title": topic,
        "subtitle": hook,
        "narration": build_narration(sections, narration_max_chars),
        "broll_query": broll_query(ticker, background),
        "duration": 6.0,
    }
