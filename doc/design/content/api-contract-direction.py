"""
타입 계약 — 영상 연출 강화(단일 배경 + 오버레이): 수치 팝·금색 강조·인트로/아웃트로 (라운드㉖)
검증: python -m mypy --strict --ignore-missing-imports api-contract-direction.py

배경 방식은 **단일 배경 유지**(사용자 확정) — ffmpeg concat/컷 전환 리스크 회피. 대신 오버레이로
리듬을 준다: (1) 차트 수치를 chart 구간에 등장(팝), (2) 종목·핵심 자막 금색 강조,
(3) 인트로/아웃트로 카드(전면 오버레이, enable 시간창). 외부 API/DB/이벤트 변경 없음(내부 렌더).
"""
from __future__ import annotations

# ── 렌더 산출 분리(㉖) — 수치 팝을 위해 차트를 2장으로 ──
# render_chart_base: 제목 + 종목 라벨(금색) + 라인차트  (수치 없음)
# render_numbers:    종가 + 등락률만(투명)  → chart 구간에 fade/scale로 등장
CHART_BASE_SUFFIX = "-chartbase.png"
NUMBERS_SUFFIX = "-numbers.png"
INTRO_SUFFIX = "-intro.png"
OUTRO_SUFFIX = "-outro.png"

# 브랜드 색(대시보드와 정합) — 금색 강조.
GOLD = "#e9b44c"

# 인트로/아웃트로 길이(초) — 전면 카드가 배경 위를 덮는 시간창.
INTRO_SEC = 0.8
OUTRO_SEC = 0.8

# 자막 색 — 핵심 구간(chart·relation)은 금색 강조, 그 외 흰색.
EMPHASIS_KINDS = ("chart", "relation")


# 자막 = (텍스트, 시작초, 끝초, 금색여부) — 기존 (텍스트,시작,끝)에 색 플래그 추가(하위호환은
# video-assembly 내부에서 처리; media.assemble 이벤트 형태는 불변 = segments[{kind,text}]).
class CaptionSpec:
    """문서용 참조 — 실제는 tuple[str, float, float, bool](video-assembly 내부)."""

    text: str
    start: float
    end: float
    gold: bool


# 수치 팝 창 — chart 구간의 (start, end). numbers 오버레이를 이 구간부터 fade-in.
# video-assembly가 segments의 chart 항목 타이밍에서 계산(이벤트 계약 불변).
POP_NOTE = "numbers 오버레이는 chart 구간 start에 fade-in(등장). scale 바운스는 후속."
