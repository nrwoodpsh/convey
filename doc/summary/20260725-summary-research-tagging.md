# 20260725 — 요약: 종목·엔티티 태깅 오탐 수정 (라운드㉜)

- **Task**: `doc/design/research/20260724-task-tagging-scope.md` · 계약 `api-contract-tagging.py`
- **작업**: /run(builder→sync) · 날짜 2026-07-25 · 브랜치 main · **로컬**(단위 검증)
- **상태**: 완료·검증(단위). 실스택 반영은 news-feed 재빌드(배포 단계).

## 개요

`tag_tickers`가 제목+본문 전체에 **단순 부분문자열**로 종목명을 매칭 → 본문에 스쳐 지나가는 종목명까지 태깅(실측: "보일러 기사→카카오"[카카오톡], "빙수 기사→카카오"[저당카카오]). 틀린 ticker가 그래프·회수 오염(알파① 위협). 해결: **제목 우선 + 본문 조건(≥2회)**.

## 변경사항 (BE)

- **`services/news-feed/app/tagging.py`**:
  - 상수 `BODY_MIN_MENTIONS = 2`.
  - `_tag_names(title, body, candidates)` — 제목에 있으면 채택, 제목엔 없고 본문 `count >= 2`면 채택, 1회 스침 제외. `_suppress_substrings`(이름-내-이름 억제) 유지.
  - `tag_tickers(title, body, dictionary=None)`·`tag_entity_names(title, body, names=None)` — 시그니처를 `(title, body)`로 변경, `_tag_names` 사용.
- **`services/news-feed/app/worker.py`**: 호출부를 `tag_tickers(title, body)`·`tag_entity_names(title, body)`로 분리. `tag_event_hints`는 결합 텍스트 유지.

## API/타입 변경

- 내부 함수 시그니처 변경(`tag_tickers`·`tag_entity_names`가 `text` → `title, body`). Kafka 이벤트 스키마·계약 불변. 계약 `api-contract-tagging.py`.

## 검증

- 단위 **10/10**(`test_tagging.py`): AC1 제목 매칭 / AC2 본문 1회 스침 미태깅(카카오톡) / AC3 본문 2회 태깅 / AC4 회귀(SK⊂SK하이닉스 억제·사전 밖 제외) / event_hints.
- mypy `--strict` 0(변경 2파일). 계약 통과. 호출부 전수 조사 — worker.py만(영향 0).

## 특이사항 (설계 대비·후속)

- **결정론 로직**이라 단위테스트가 오탐 케이스를 직접 증명(실스택 관찰 불필요). 실스택 반영은 news-feed **재빌드**(배포 단계).
- **휴리스틱 한계(정직)**: 본문에 "카카오톡"이 2회↑ 나오는 메시징 기사는 여전히 태깅될 수 있음 — 제목 우선이 대부분 거르나 완벽 X. 동음이의 예외 보강은 후속.
- **기존 오염 데이터**(2,898건·그래프): 이번 범위 밖 — 신규 수집부터 교정. 재태깅 배치는 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
