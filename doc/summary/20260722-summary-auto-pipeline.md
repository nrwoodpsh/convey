# 20260722 — 요약: 자동 양산 루프 (이슈 선별 → 자동 제작)

- **Task**: `doc/design/issue-detector/task-auto-pipeline-20260722.md` (라운드⑬, 알파4)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 Kafka·content_db)
- **상태**: 이슈 선별(issue-detector)과 제작(content)을 이어 **자동 양산** 완성. 5개 AC 충족.

## 개요

지금까지 사람이 `POST /content/generate`로 종목을 수동 투입해야 했다. issue-detector가 상위 이슈를 주기적으로 `issue.selected`로 발행하고, content가 소비해 **자동으로 잡을 생성**하도록 이어붙였다. "이슈 뜨면 알아서 쇼츠 생성"(알파4). **발행은 여전히 사람 승인**(가드레일 불변) — 자동은 `ready`까지.

## 변경사항 (BE)

**issue-detector**
- `worker.py` — `run_emitter`(KafkaProducer + 주기 발행 루프): `ranker.top` → score 임계 초과 + 상위K + 종목 쿨다운만 `issue.selected` 발행.
- `main.py` — emit 루프 백그라운드 등록. `config.py` — `topic_issue_selected`·`emit_interval`·`emit_top_k`·`score_threshold`·`cooldown_seconds`.

**content**
- `consumer.py` — `handle_issue`(issue.selected → `service.start_generation`, owner_id="auto") + `run_issue_consumer`.
- `main.py` — issue 소비자 등록. `config.py` — `topic_issue_selected`.

**계약**
- `doc/design/issue-detector/api-contract.py` — `IssueSelectedEvent`·`TOPIC_ISSUE_SELECTED`. (조회 상태 GET /issues/today는 유지, 선별 발행만 추가.)

## 검증 (실 Kafka·content_db·로컬)

- **AC2/AC4**: 랭커에 005930(등락 큰 2틱→score 2.3)·000660(변화0→score 0) 주입 → `run_emitter`가 **005930만 발행**, 000660(임계 0.5 미달) 제외, 여러 주기에도 **쿨다운으로 1건**(중복 0).
- **AC3**: `issue.selected` → `handle_issue` → `start_generation` → GenerationJob(**pending·owner=auto**) 생성 + `content.generate` 발행(수동 POST와 동일 경로).
- **AC5**: 자동 잡은 `pending`(→ 파이프라인 → ready), **자동 승인 없음**(발행은 사람).
- mypy --strict clean, contract-gate clean, 랭킹 단위 4 회귀 없음.

## 특이사항 (후속)

- **가드레일 유지**: 자동은 생성(ready)까지, 발행(승인)은 사람. 무한·중복 양산은 score 임계 + 쿨다운으로 억제.
- 랭킹은 in-memory·재기동 시 초기화 → 재기동 직후 소수 중복 가능. **A2(history_search, 중복회피)**가 붙으면 content 레벨에서 보완(A1의 짝).
- **후속(B)**: 게이트웨이 경유 e2e, 내레이션 길이, broll 검색어 매핑, 전체 in-container e2e 등.
- 커밋: 아직(사람 게이트 — `/commit`).
