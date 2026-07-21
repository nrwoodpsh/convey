"""
API 계약 — 라운드 ⑤: 근거 기반 쇼츠 end-to-end (키 없는 코어) · 알파1·3·4 · ADR 0006·0008
검증: python -m mypy --strict --ignore-missing-imports api-contract-pipeline-keyless.py

부품(agent build_script·render_chart·build_short)은 완성. 이 계약은 **오케스트레이션 배선**을
정본화한다: content가 잡을 몰고, agent가 근거 스크립트를 만들고(east-west HTTP),
video-assembly가 정확 차트+합성으로 mp4를 만든다(이벤트).

키 없는 경로: 외부 broll/TTS 미사용. 배경=로컬 생성 타이틀 카드, 오디오=무음(anullsrc).
image.generate·tts.generate fan-out(media 계약)은 키 발급 후 라운드로 미룬다.
가드레일: 스크립트 수치는 사실 슬롯에서만(환각0), 차트 수치는 PriceTick과 1:1, 원문 외부반출 0.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# ── 1) 가격 근거: research /search 확장 (PriceTick 사실 → 스크립트·차트 공급) ──
# research api-contract.py SearchResponse에 optional `price` 필드로 추가(빌더에서 정합).


class PriceEvidence(BaseModel):
    """최신 종가·등락률·시계열 — research_db PriceTick에서 산출(사실). 무출처 금지."""

    ticker: str
    close: float
    change_pct: float  # 창 내 첫→끝 종가 변화율
    series: list[float] = Field(default_factory=list)  # 차트용 종가 시계열(정확 값)
    source_url: str  # 가드레일
    ref_id: int  # PriceTick id


# ── 2) agent 스크립트 생성 엔드포인트 (content → agent, east-west + HMAC) ──
SCRIPT_ENDPOINT = ("POST", "/agent/script")


class ScriptRequest(BaseModel):
    job_id: int
    topic: str = Field(min_length=1, max_length=200)
    ticker: str | None = None


class CitationDTO(BaseModel):
    claim: str
    source_url: str  # 가드레일: 무출처 금지
    ref_id: int


class ScriptSectionDTO(BaseModel):
    kind: str  # 'hook' | 'chart' | 'fact' | 'closing'
    text: str
    data_slots: dict[str, str] = Field(default_factory=dict)  # 정확 수치(사실에서만)


class ChartData(BaseModel):
    """차트 렌더 입력 — video-assembly ChartOverlay와 1:1(사실 수치)."""

    ticker: str
    close: float
    change_pct: float
    series: list[float] = Field(default_factory=list)


class ScriptResponse(BaseModel):
    sections: list[ScriptSectionDTO] = Field(default_factory=list)
    citations: list[CitationDTO] = Field(default_factory=list)  # 모든 수치 결속
    chart: ChartData | None = None  # 근거 없으면 None(스크립트만)


# ── 3) 오케스트레이션 이벤트 (키 없는 경로) ──
TOPIC_MEDIA_ASSEMBLE = "media.assemble"  # content → video-assembly
TOPIC_CONTENT_ASSEMBLED = "content.assembled"  # video-assembly → content (fan-in)


class MediaAssembleEvent(BaseModel):
    """content → video-assembly. 외부 자산 없음(키X): 배경 로컬 생성·오디오 무음."""

    job_id: int
    chart: ChartData  # 정확 수치·시계열(알파3)
    title: str  # 배경 타이틀 카드 문구(로컬 렌더)
    subtitle: str  # 자막(스크립트 hook/요약)
    duration: float = 6.0


class ContentAssembledEvent(BaseModel):
    """video-assembly → content. mp4 경로(로컬 볼륨) 회신 → 잡 ready(내부 상태)."""

    job_id: int
    ok: bool
    mp4_path: str | None = None
    error: str | None = None


# ── 참고: 기존 계약 재사용 ──
# - content 잡 상태머신·JobStatus·GenerateReq·Citation·Script: content/api-contract.py
# - ChartOverlay·AssembleSpec(외부 자산 경로): media/api-contract.py (키 발급 후 fan-out)
# 이번 라운드는 위 키 없는 경로만 배선한다.
