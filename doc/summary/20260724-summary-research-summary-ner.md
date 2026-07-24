# 20260724 — 요약: 요약 선행 NER + LLM 출력 상한 (라운드㉛)

- **Task**: `doc/design/research/20260724-task-summary-ner.md` · 계약 `api-contract-summary-ner.py` · ADR 0015
- **작업**: /run(design→builder→sync) · 날짜 2026-07-24 · 브랜치 main · **로컬 실 컨테이너 스택**
- **상태**: 완료·검증. 백필 타임아웃(하드) 제거 + 추론모델 빈 요약 문제 해결.

## 개요

전량 백필(`--llm`)이 **타임아웃 다발로 중단**(실측 성공 8/타임아웃 9). 원인은 긴 기사 본문을 로컬 LLM에 통째로 넣어 생성이 240초 초과. 해결: **긴 본문(>1,500자)은 요약 선행 → 요약 위에서 개방형 NER**, 요약 호출은 **출력 상한(num_predict)** 강제. 환각 방지(알파1)는 **원문 본문 검증**으로 보존(요약이 지어낸 엔티티 폐기). 구현 중 실효 모델이 추론형 `qwen3:14b`임이 드러나 **think 끄기 + keep_alive 고정**을 추가.

## 변경사항 (BE)

- **llm-inference** (`main.py`·`ollama_client.py`):
  - `build_generate_payload(model, prompt, num_predict, think, keep_alive)` — 지정 옵션만 포함(하위호환).
  - `GenerateReq`에 `num_predict`·`think`·`keep_alive`(모두 선택). `OllamaClient.generate(...)` 전달.
- **research** (`extract/relations.py`):
  - 상수 `SUMMARY_THRESHOLD=1500`·`SUMMARY_NUM_PREDICT=256`.
  - `build_summary_prompt`·`summarize(text, llm)`.
  - `extract_graph(..., *, verify_text=None)` — NER 입력은 text, **환각 검증은 verify_text(원문)**.
  - `extract_article_graph(body, seed, llm, llm_summary, *, summary_threshold)` — 길이 분기(요약↔원문).
- **research 배선** (`consumer.py`·`backfill.py`):
  - `_llm_caller(num_predict=None)` — payload에 `think=False`·`keep_alive="30m"` 상시, `num_predict` 조건부.
  - `llm`(NER) + `llm_summary`(상한) 두 caller → `extract_article_graph` 사용. 백필 직렬 유지.

## API 변경

- `POST /generate`(llm-inference): 요청에 선택 필드 `num_predict`·`think`·`keep_alive` 추가. 미지정 시 기존 동작 불변(하위호환). 계약 `api-contract-summary-ner.py`.

## 검증 (실 컨테이너 스택)

- 단위 **12/12**: research 8(요약 분기·원문검증 환각컷 포함), llm-inference 4(payload 옵션 포함/생략).
- mypy `--strict` 0 이슈(변경 5파일), 계약 게이트 통과.
- 실스택(재빌드 후): `--limit 10` 백필 **완주·타임아웃 0**(이전 9/17≈53%→0), 그래프 173→215 노드.
- think=False 프로브: 요약 **22초·416자**(이전 num_predict=64 → 211초·0자 빈 응답 대비 해결).

## 특이사항 (설계 대비·후속)

- **이탈(설계 결함 발견→정지→사용자 결정)**: `.env` `OLLAMA_MODEL=qwen3:14b`(추론모델). num_predict 상한이 `<think>`만 채워 빈 요약 → builder 중 멈추고 사용자 결정(**think 끄기+keep_alive 고정**) 후 적용. ADR 0015에 기록.
- **드리프트 정정**: README 모델 표기 `llama3.2`(config 기본) → **`qwen3:14b`**(.env 실효)로 수정.
- **후속**: `--limit 10` 표본은 모두 짧은 기사(요약 경로 미탐색) — 요약 경로는 프로브로 직접 검증. 전량 백필 재개는 사람 실행(`app.backfill --llm`). num_ctx 튜닝·요약 품질(관계 회수) 관측은 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
