# 20260725 — 요약: 이슈 선별 news_count 중복 제거 (라운드㊲)

- **Task**: `doc/design/issue-detector/20260725-task-issue-dedup.md` · 계약 `api-contract-issue-dedup.py`
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택 검증
- **상태**: 완료·검증(단위 + 라이브).

## 개요

issue-detector의 `RollingRanker.ingest_news`가 `research.ingested`마다 무조건 +1 → 5분 재발행 중복이 `news_count`를 부풀려 score **812**(정상 18~) 폭발·랭킹 왜곡(§6 실측). 해결: **윈도우 내 유일 source_url만 카운트**(멱등). score 공식·가중치·임계 불변.

## 변경사항 (BE)

- **`services/issue-detector/app/ranking.py`**:
  - `_TickerState.news`: `list[datetime]` → **`dict[str, datetime]`**(source_url → ts).
  - `ingest_news(ticker, source_url, ts)` — `news[source_url] = ts`(중복 자동 제거·최신 갱신).
  - `_metrics`: `news_count = sum(1 for ts in st.news.values() if ts >= since)`.
- **`services/issue-detector/app/worker.py`**: `on_news`가 `event["source_url"]`을 `ingest_news`에 전달.

## API/타입 변경

- 내부 `ingest_news` 시그니처 `(ticker, ts)` → `(ticker, source_url, ts)`. Kafka 이벤트·계약 불변(이미 event에 source_url 있음). 계약 `api-contract-issue-dedup.py`.

## 검증

- 단위 **5/5**(`test_ranking.py`): 중복 3회→count 1(신규) · 다른 url 2건 · 윈도우 경계 · z-score·정렬 회귀.
- mypy `--strict` 0(변경 2파일). 호출부 전수 — worker.py만.
- **실스택**(재빌드): 같은 url 5회 재발행 + 유일 1건 → `news_count = 2`(6 아님) 라이브 확인 → **score 폭발 소멸**.

## 특이사항 (설계 대비·후속)

- **발행측 재발행 자체**(news-feed 5분 중복)는 별개 — ㉝(수집 재설계)에서 다룸. 여기선 소비측 카운트만 교정.
- **메모리 롤링윈도우** 유지 — 재시작 시 윈도우 유실은 별도 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
