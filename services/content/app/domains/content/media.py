"""미디어 오케스트레이션 공용 헬퍼(라운드㉓) — 내레이션·broll 검색어·assemble 이벤트 구성.

consumer(자동/수동 스크립트)와 service(승인 후 합성)가 **동일한 assemble 이벤트**를 만들도록
순수 함수로 분리(순환 import 방지: consumer→service, service→media, consumer→media).
"""
from __future__ import annotations

import re
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


# 배경 컷 전환용 보조 검색어(㉙/D) — 첫 개는 대표(산업/애니), 뒤는 다양성.
_BG_EXTRA_REAL = ("seoul city skyline aerial", "abstract technology blue")
_BG_EXTRA_ANIM = ("glowing particles blue", "digital data network abstract")


def broll_queries(ticker: str | None, background: str = "real") -> list[str]:
    """배경 컷 전환용 복수 검색어(㉙/D) — 대표 + 보조 2개. 중복 제거."""
    primary = broll_query(ticker, background)
    extra = _BG_EXTRA_ANIM if background == "anim" else _BG_EXTRA_REAL
    out: list[str] = []
    for q in (primary, *extra):
        if q and q not in out:
            out.append(q)
    return out


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


def select_segments(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """낭독·자막 구간(㉕/C) — 훅→수치→인과→사실→거시 순으로 대표 섹션 1개씩. chart 슬롯 해소.

    각 구간 = {kind, text}. 내레이션·구간 자막이 같은 소스를 쓰도록 단일 선택.
    """
    segs: list[dict[str, str]] = []
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
            segs.append({"kind": kind, "text": text.strip()})
    return segs


def build_narration(sections: list[dict[str, Any]], max_chars: int) -> str:
    """내레이션(음성 낭독용) — 구간 텍스트를 문자 예산 내로 이어붙임(구간 선택과 동일 소스)."""
    return clip(" ".join(s["text"] for s in select_segments(sections)), max_chars)


def build_trust(citations: list[dict[str, Any]] | None, date: str) -> dict[str, str] | None:
    """신뢰 배지(㉕/C2) — 첫 뉴스 출처 호스트 + 날짜. 무출처면 None(가드레일)."""
    for c in citations or []:
        url = str(c.get("source_url", ""))
        m = re.search(r"https?://([^/]+)", url)
        host = m.group(1).lstrip("www.") if m else ""
        if host and "krx.co.kr" not in host:  # 시세(krx) 말고 뉴스 출처 우선
            return {"source_host": host, "published_date": date}
    return None


def build_assemble_event(
    *,
    job_id: int,
    topic: str,
    ticker: str | None,
    chart: dict[str, Any],
    sections: list[dict[str, Any]],
    narration_max_chars: int,
    background: str = "real",
    citations: list[dict[str, Any]] | None = None,
    date: str = "",
) -> dict[str, Any]:
    """media.assemble 이벤트 — 자동/승인 공용. segments=구간 자막·음성(㉕/C), trust=신뢰 배지."""
    hook = next((s["text"] for s in sections if s.get("kind") == "hook"), topic)
    segments = select_segments(sections)
    return {
        "job_id": job_id,
        "chart": chart,
        "title": topic,
        "subtitle": hook,  # 폴백(구간 없을 때 단일 자막)
        "narration": build_narration(sections, narration_max_chars),  # 폴백(구간 없을 때 단일 음성)
        "segments": segments,  # [{kind,text}] — 구간 TTS·싱크 자막
        "trust": build_trust(citations, date),
        "broll_query": broll_query(ticker, background),  # 단일(폴백)
        "broll_queries": broll_queries(ticker, background),  # 복수(㉙/D 컷 전환)
        "duration": 6.0,
    }
