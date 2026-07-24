"""타입 계약 — 요약 선행 NER + LLM 출력 상한 (라운드㉛, ADR 0015).

검증: python -m mypy --strict --ignore-missing-imports api-contract-summary-ner.py

목적: 긴 기사 본문을 로컬 Ollama로 먼저 요약(**출력 상한 강제**) → 요약 위에서 개방형 NER.
      타임아웃(기사당 240초 초과) 다발을 해소하되, 환각 방지(알파1)는 유지 —
      추출 엔티티는 **원문 본문**에 실재해야 채택(요약이 지어낸 엔티티 폐기).

기존 계약 api-contract-ner.py(개방형 NER)를 대체하지 않고 확장한다. 텍스트 LLM은 로컬 Ollama만.
함수 시그니처는 Protocol로 표현(구현 아님).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

# 프롬프트→응답 문자열. 출력 상한(num_predict)은 호출 경계(make_llm_caller)에서 바인딩.
LlmCaller = Callable[[str], str]

# 기존과 동일(㉚) — 재확인용.
EDGE_TYPES: tuple[str, ...] = ("HAS_EVENT", "AFFECTS", "SUPPLIES", "COMPETES", "BELONGS_TO")
ENTITY_MIN_LEN = 2

# ── 튜닝 상수(신규, research/app/extract/relations.py) ──
SUMMARY_THRESHOLD: int = 1500       # 본문 char > 이 값이면 요약 선행. 이하는 원문 그대로 NER.
SUMMARY_NUM_PREDICT: int = 256      # 요약 호출 출력 토큰 상한 — 타임아웃 방지 핵심.


@dataclass
class ExtractedRelation:
    subject: str
    edge: str
    object: str


@dataclass
class ExtractedGraph:
    entities: list[str] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)


# ── 1) llm-inference: 출력 상한 파라미터 (services/llm-inference) ──
class GenerateReq(Protocol):
    """POST /generate 요청. 신규 필드는 모두 선택 — 미지정 시 기존 동작."""

    prompt: str
    model: str | None
    num_predict: int | None  # 출력 토큰 상한. Ollama options.num_predict.
    think: bool | None       # 추론모델 <think> 억제(qwen3 등). payload.think.
    keep_alive: str | None   # 모델 상주 시간(예 "30m") — 재적재 방지. payload.keep_alive.


class OllamaGenerate(Protocol):
    """OllamaClient.generate — 지정된 옵션만 payload에 포함(미지정은 생략, 하위호환)."""

    def __call__(
        self,
        prompt: str,
        model: str | None = ...,
        num_predict: int | None = ...,
        think: bool | None = ...,
        keep_alive: str | None = ...,
    ) -> str: ...


# ── 2) research 추출: 요약 + 원문검증 NER (services/research/app/extract/relations.py) ──
class Summarize(Protocol):
    """본문 요약(로컬 Ollama). llm은 출력 상한이 바인딩된 caller(SUMMARY_NUM_PREDICT).

    프롬프트: 핵심 사실·엔티티 보존, 새 정보 추가 금지, 3~5문장. (build_summary_prompt)
    """

    def __call__(self, text: str, llm: LlmCaller) -> str: ...


class ExtractGraph(Protocol):
    """개방형 NER. NER 입력은 text, **환각 검증은 verify_text**(없으면 text).

    요약 경로: text=요약, verify_text=원문 → 엔티티는 원문 실재만 채택(알파1 보존).
    verify_text 미지정 시 기존 동작(㉚)과 동일 — 하위호환.
    """

    def __call__(
        self,
        text: str,
        seed_entities: list[str],
        llm: LlmCaller,
        *,
        verify_text: str | None = ...,
    ) -> ExtractedGraph: ...


class ExtractArticleGraph(Protocol):
    """오케스트레이션 — 긴 본문은 요약 후 NER(원문검증), 짧은 본문은 원문 NER.

    len(body) <= threshold: extract_graph(body, seed, llm)
    len(body) >  threshold: s = summarize(body, llm_summary);
                            extract_graph(s, seed, llm, verify_text=body)
    seed_entities는 항상 원문 기준(news-feed가 본문 매칭으로 뽑은 고정확 seed).
    """

    def __call__(
        self,
        body: str,
        seed_entities: list[str],
        llm: LlmCaller,
        llm_summary: LlmCaller,
        *,
        summary_threshold: int = ...,
    ) -> ExtractedGraph: ...


# ── 3) 호출 경계: 출력 상한 바인딩 (consumer.py / backfill.py) ──
class MakeLlmCaller(Protocol):
    """llm-inference /generate 호출 클로저 생성. num_predict를 요청 본문에 포함.

    배선: llm = make_llm_caller()                          # NER(무제한)
          llm_summary = make_llm_caller(SUMMARY_NUM_PREDICT)  # 요약(상한)
    """

    def __call__(self, num_predict: int | None = ...) -> LlmCaller: ...


# ── 동시성(백필) ──
# 백필은 직렬(한 번에 1건)·저부하 유지 — 라이브 news-feed NER와 Ollama 경합 최소화.
# 요약으로 건당 시간이 짧아져 경합해도 완주 가능(별도 일시정지 없음). 멱등이라 재개 안전.
BACKFILL_CONCURRENCY_NOTE = "backfill: 직렬 for 루프 유지. 병렬화 금지(Ollama 포화 방지)."
