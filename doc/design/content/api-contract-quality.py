"""
API/타입 계약 — 품질 향상(알파 복원): 그래프 인과 투입 · LLM 편집자 · 연출 (라운드㉕)
검증: python -m mypy --strict --ignore-missing-imports api-contract-quality.py

배경: 현재 영상은 헤드라인+수치 나열. 알파("그날 기사 × 그래프 인과")가 코드에서 끊겨 있음
  — agent Evidence에 relations가 없어 research /search의 관계(RelationHit)를 버린다.
  이 계약은 (A)관계를 스크립트까지 흘리고, (B)LLM을 연결자로, (C)연출 데이터를 실어 나른다.
단계: Phase A(데이터) → B(문장) → C(연출). 가드레일: 수치·관계는 사실/근거 결속(환각 0).
"""
from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

# ══ Phase A — 그래프 인과 투입 + 사실 큐레이션 ══

# research /search는 이미 RelationHit(subject, edge, object, source_article_id, source_url) 반환.
# agent가 이를 버리지 않도록 Evidence·스크립트에 투입한다(신규 타입).


class RelationEvidence(TypedDict):
    """그래프 인과 근거 — agent가 research /search의 relations를 받아 스크립트에 결속.

    edge ∈ {HAS_EVENT, AFFECTS, SUPPLIES, COMPETES, BELONGS_TO}. 근거=source_article_id.
    """

    subject: str
    edge: str
    object: str
    source_url: str  # 가드레일: 무출처 관계 제외
    article_id: int


# agent Evidence(retriever) 확장 — 기존 price·series·facts·macros + relations 추가.
#   (구현: services/agent/app/rag/retriever.py Evidence dataclass에 relations 필드)

# ScriptSection.kind 확장: 기존 hook|chart|fact|macro|closing + **relation**(인과 문장).
SCRIPT_SECTION_KINDS = ("hook", "chart", "relation", "fact", "macro", "closing")

# 엣지 → 한국어 서술 매핑(관계 문장 생성용, 수치 아님·환각 아님 — 사실 관계의 한국어화).
EDGE_KO: dict[str, str] = {
    "AFFECTS": "{s}이(가) {o}에 영향",
    "SUPPLIES": "{s}이(가) {o}에 공급",
    "COMPETES": "{s}과(와) {o}가 경쟁",
    "BELONGS_TO": "{s}은(는) {o} 소속",
    "HAS_EVENT": "{s}에 {o} 이슈",
}


class FactHitRanked(BaseModel):
    """research /search 사실에 중요도·중복키 부여(P3). 헤드라인 나열·중복 방지."""

    text: str
    source_url: str
    ref_id: int
    score: float = 0.0  # 중요도(issue-detector 점수/최신성 기반). 정렬·상위 선별용
    dedup_key: str = ""  # 제목 정규화 키(near-duplicate 병합용)


# ══ Phase B — LLM 편집자(연결·해석 문장, 수치는 슬롯 고정) ══

# build_script: LLM이 훅뿐 아니라 **연결 문장**(fact/relation을 엮는 prose)을 쓴다.
#   단 수치·관계 주장은 data_slots·relations(사실)에 결속 — LLM은 문장만, 값은 안 만든다.
# 거시(macro)도 원시 숫자 덤프 → 문장화("{name} {value}{unit}로 …")하되 값은 슬롯.
# 계약상 새 타입 없음(ScriptSection 유지). 프롬프트·조립은 task Logic 참조.


# ══ Phase C — 연출(장면 전환·자막 싱크·신뢰 배지·TTS) ══


class SceneSegment(BaseModel):
    """내레이션 비트 1개 — 장면 전환·자막 싱크 단위(P6·P7). video-assembly가 구간별로 렌더."""

    kind: str  # SCRIPT_SECTION_KINDS 중
    caption: str  # 이 구간 자막(내레이션과 일치)
    narration: str  # 이 구간 음성 문장(TTS)
    emphasize_number: bool = False  # 수치 구간이면 화면에 크게 팝


class TrustBadge(BaseModel):
    """정확 데이터 알파를 시청자가 체감 — 출처·날짜 배지(작게). 무출처면 미표시."""

    source_host: str  # 예: 한국경제 (source_url 호스트)
    published_date: str  # YYYY-MM-DD (기사/시세 기준일, UTC)


class MediaAssembleEventV2(BaseModel):
    """media.assemble 확장(Phase C) — 연출 데이터. 기존 필드(job_id·chart·title·broll_query)는 유지.

    segments가 있으면 구간별 장면·자막·수치 팝; 없으면 기존 단일 자막(하위호환).
    """

    job_id: int
    chart: dict[str, float | str | list[float]]
    title: str
    broll_query: str
    background: str = "real"  # real | anim
    segments: list[SceneSegment] = Field(default_factory=list)  # 비면 기존 동작
    trust: TrustBadge | None = None
    duration: float = 30.0


# ══ 에러/토픽 — 기존 재사용 ══
# 신규 엔드포인트 없음(내부 파이프라인 개선). research 백필은 관리 스크립트/일회성.
BACKFILL_NOTE = "P2 백필: 기존 articles 재추출은 scripts 또는 일회성 관리 작업(엔드포인트 아님)."
