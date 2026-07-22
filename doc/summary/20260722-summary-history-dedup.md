# 20260722 — 요약: 히스토리 조회 + 자동 양산 중복회피 (A2)

- **Task**: `doc/design/content/task-history-dedup-20260722.md` (라운드⑭, 알파4)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 content_db·Kafka)
- **상태**: `history_search` 스텁 제거 + 자동 양산 중복회피. A1(자동 루프)의 짝 완성. 5개 AC 충족.

## 개요

마지막 스텁(`history_search`)을 구현하고, 자동 양산이 같은 종목을 반복 생성하지 않도록 중복회피를 붙였다. 자동 경로(handle_issue)만 dedup — 수동 생성은 명시 의도라 그대로. 벡터 아님(키워드/메타, ADR 0006).

## 변경사항 (BE, content)

- `domains/content/repository.py` — `history_search` **구현**(contents ⨝ generation_jobs, topic ILIKE, 최신순 top_k → (content_id, topic)). `recent_ticker_job`(같은 ticker·최근 window·status≠failed → bool) 신설.
- `domains/content/service.py` — `search_history`가 `history_search` 사용 → `SearchHit` 목록(스텁 제거).
- `consumer.py` — `handle_issue`에 dedup 가드: `recent_ticker_job`이면 자동 생성 skip.
- `config.py` — `dedup_window_days=1`.

## API/계약 변경

- 없음(기존 `SearchHit`/`SearchResponse`·스키마 그대로). 마이그레이션 없음.

## 검증 (실 content_db·Kafka·로컬)

- **AC2**: `history_search('테스트종목')` → 해당 content_id 반환(스텁 제거).
- **AC3**: 무매칭 키워드 → 빈 목록(에러 아님).
- **AC4**: `recent_ticker_job` 판정 + `handle_issue` 같은 종목 2회 호출 → 잡 1건(2회차 skip, 중복회피).
- **AC5**: 수동 `start_generation` 같은 종목 2회 → 잡 2건(dedup 미적용 — 명시 의도).
- mypy --strict clean.

## 특이사항 (후속)

- **A1의 짝 완성**: 자동 루프(A1)가 재기동·주기마다 같은 종목을 재생성하던 것을 window(기본 1일)로 억제. 진행 중 잡도 중복으로 봐 재기동 직후 재발행까지 방지. 실패(failed) 잡은 재시도 허용.
- **후속(B)**: 게이트웨이 경유 e2e, 내레이션 길이, broll 검색어 매핑, 전체 in-container e2e, 타입 그래프 노드 등.
- 커밋: 아직(사람 게이트 — `/commit`).
