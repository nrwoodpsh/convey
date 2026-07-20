"""
API 계약 — 라운드 ④: 미디어·정확 렌더 (video-assembly + image-gen·tts) · 알파3 · ADR 0003·0006
검증: python -m mypy --strict --ignore-missing-imports api-contract.py

외부(커모디티): broll·TTS. 우리(알파3): **화면 위 정확 차트·수치 오버레이 + ffmpeg 합성**.
생성형 영상은 POC 제외(ADR 0006). 미디어 바이너리 = 로컬 볼륨(POC), MinIO/S3는 후속.
가드레일: 외부 호출은 프롬프트·에셋만(원문 전체 반출 금지).
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# fan-out 이벤트 (content → 미디어 외주)
TOPIC_IMAGE_GENERATE = "image.generate"
TOPIC_TTS_GENERATE = "tts.generate"


class ImageGenerateEvent(BaseModel):
    job_id: int
    prompt: str = Field(description="배경 broll 프롬프트 — 원문 전체 반출 금지")
    asset_key: str


class TtsGenerateEvent(BaseModel):
    job_id: int
    text: str = Field(description="내레이션 텍스트(대본)")
    asset_key: str


# 정확 렌더 스펙 (우리 통제 — 결정론적)
class ChartOverlay(BaseModel):
    ticker: str
    close: float
    change_pct: float
    series: list[float] = Field(default_factory=list, description="차트 시계열(정확 값)")


class AssembleSpec(BaseModel):
    job_id: int
    background_asset: str  # 외부 broll/스톡
    voice_asset: str  # 외부 TTS
    overlays: list[ChartOverlay] = Field(default_factory=list)  # 정확 수치·차트
    subtitles: list[str] = Field(default_factory=list)


class MediaError(tuple[str, int, str], Enum):
    ASSET_MISSING = ("MED001", 404, "필요 자산이 없습니다.")
    RENDER_FAILED = ("MED002", 500, "합성에 실패했습니다.")
