"""타입 계약 — 종목·엔티티 태깅 오탐 완화(제목 우선 + 본문 조건). 라운드㉜.

검증: python -m mypy --strict --ignore-missing-imports api-contract-tagging.py

배경: `tag_tickers`가 제목+본문 전체에 **단순 부분문자열**(`name in text`)로 매칭 →
본문에 스쳐 지나가는 종목명까지 태깅(예: 보일러 기사 "카카오톡"→카카오, 빙수 기사 "저당카카오"→카카오).
잘못된 ticker가 그래프에 틀린 엣지·회수를 만들어 알파①(정확) 훼손.

해결: **제목에 있으면 확정, 본문에만 있으면 등장 횟수 조건**(제목 우선 + 본문 조건).
결정론 유지(LLM 미사용), 사전 밖 태깅 0(환각 방지) 불변.
"""
from __future__ import annotations

from typing import Protocol

# 본문 단독(제목에 없음) 태깅 최소 등장 횟수. 1회 스침은 제외, N회 실질 언급만 채택.
BODY_MIN_MENTIONS: int = 2


class TagNames(Protocol):
    """공유 규칙 — 후보 이름들을 제목 우선 + 본문 조건으로 매칭해 **이름** 목록 반환.

    - name이 title에 있으면 → 채택(확정).
    - title엔 없고 body.count(name) >= BODY_MIN_MENTIONS → 채택.
    - 그 외(본문 1회 스침) → 제외.
    이름-내-이름 부분문자열 억제(_suppress_substrings)는 그대로 적용(SK ⊂ SK하이닉스).
    """

    def __call__(self, title: str, body: str, candidates: tuple[str, ...]) -> list[str]: ...


class TagTickers(Protocol):
    """종목 태깅 — 위 규칙으로 매칭된 이름을 **ticker 코드**로 변환(등장 순서·중복 제거).

    (변경) 기존 `tag_tickers(text)` → `tag_tickers(title, body)`로 분리(매칭 범위 구분).
    """

    def __call__(
        self, title: str, body: str, dictionary: dict[str, str] | None = ...
    ) -> list[str]: ...


class TagEntityNames(Protocol):
    """엔티티(종목+섹터) 이름 태깅 — 동일 규칙 적용(그래프 seed 오탐도 함께 차단).

    (변경) `tag_entity_names(text)` → `tag_entity_names(title, body)`.
    """

    def __call__(
        self, title: str, body: str, names: tuple[str, ...] | None = ...
    ) -> list[str]: ...


# ── 변경 요약 ──
# - tagging.py: 내부 공유 `_tag_names(title, body, candidates)` 신설, tag_tickers·tag_entity_names가 사용.
# - worker.py: 호출부를 title·body 분리 전달로 수정(기존 text=title+" "+body 결합 제거).
# - event_hints(tag_event_hints)는 변경 없음(단순 키워드 힌트, 결합 텍스트 유지 허용).
CHANGE_NOTE = "제목 우선 + 본문 >=BODY_MIN_MENTIONS. 기존 데이터 재태깅은 후속(별도 스크립트)."
