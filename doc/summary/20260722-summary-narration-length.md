# 20260722 — 요약: 내레이션 길이 조절 (B2)

- **Task**: `doc/design/content/task-narration-length-20260722.md` (라운드⑮, 쇼츠 완성도)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 edge-tts)
- **상태**: 내레이션(음성)을 축약해 쇼츠 길이 단축. 스크립트·자막·인용은 전체 유지. 5개 AC 충족.

## 개요

내레이션이 스크립트 전체(거시·사실 전부)를 낭독해 음성이 ~38s로 길었다. **음성 낭독 텍스트만** 핵심 섹션(hook·chart·대표 사실·거시)으로 축약하고 문자 예산(기본 180자)을 두어 길이를 줄였다. 근거(자막·citations)는 그대로 유지.

## 변경사항 (BE, content)

- `consumer.py` — `_narration`을 **대표 섹션 축약**(각 kind 1개: hook·chart·fact·macro) + `_clip`(문자 예산 초과 시 문장/단어 경계 컷). `handle_generate`가 `settings.narration_max_chars` 전달.
- `config.py` — `narration_max_chars=180`.

## API/계약 변경
- 없음. 마이그레이션 없음.

## 검증 (실 edge-tts·로컬)

- **AC2**: 거시 5·사실 여럿 샘플 → 예산(180자) 이내, hook·종목(005930)·종가·등락률·대표 사실 포함, 사실은 대표 1개만.
- **AC3**: 긴 스크립트(249자) → 축약(135자). **실 edge-tts 음성 35.7s → 20.4s(43% 단축)**.
- **AC4**: `_narration`은 음성 텍스트만 생성 — `Script`(sections·citations) 저장·`subtitle`(hook) 경로 불변 → 근거·자막 전체 유지(구조적).
- **AC5**: mypy --strict clean.

## 특이사항 (이탈·후속)

- **한계**: 거시 섹션이 한 줄에 여러 지표를 담아 "대표 거시 1개"가 사실상 전체 거시 문장 → **문자 예산이 실질 상한**. 거시 섹션을 지표별로 분리하면 대표화 정밀도↑(후속).
- 축약은 **음성만** — 자막·인용(알파1 근거)은 전체 유지.
- 커밋: 아직(사람 게이트 — `/commit`).
