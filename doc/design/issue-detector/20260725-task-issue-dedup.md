# 20260725-task-issue-dedup.md

> 라운드 ㊲ (이슈 선별 news_count 중복 제거 — score 폭발 수정). 알파②.
> 계약: `api-contract-issue-dedup.py`. issue-detector(`ranking.py`·`worker.py`). DB 없음(메모리 롤링) 유지.

## 1. Requirements
- **문제(§6 실측)**: `issue.selected`에서 삼성전자 score **812**(정상 18~). 원인: `RollingRanker.ingest_news`가 `research.ingested` 올 때마다 **무조건 +1** → **5분 재발행 중복**(research.ingested 8만 건)이 `news_count`를 부풀림 → 점수 폭발·랭킹 왜곡. research는 `source_url` 멱등이나 issue-detector는 아님.
- **목표**: 윈도우 내 **유일 source_url만 카운트**(멱등). score 공식·가중치·임계·윈도우 불변 — 중복만 제거.
- **Acceptance Criteria**:
  - [ ] AC1: 같은 `source_url` 재수신은 news_count 안 늘림. **검증: 단위 — 같은 url 3회 ingest → news_count=1.**
  - [ ] AC2: 다른 url은 각각 카운트. **검증: url 2개 → news_count=2.**
  - [ ] AC3: 윈도우 밖(오래된) 뉴스는 제외(기존 유지). **검증: since 이전 ts 제외.**
  - [ ] AC4: 회귀 — 기존 ranking 테스트 통과, score 공식·top·임계 불변. mypy·계약.

## 2. 핵심 결정 & 사각지대
- **결정**: 중복 제거는 **issue-detector 내부**(source_url 집합) — 발행측(news-feed) 재발행 자체는 별개(㉝ 수집 재설계에서 다룸). 여기선 소비측 카운트만 교정.
- **사각지대**: `_TickerState.news`가 list→dict(source_url→ts)로 메모리 구조 변경(경미). 메모리 롤링이라 재시작 시 유실은 여전(별도 후속). event에 source_url 항상 존재(news-feed 가드레일) — 없으면 skip.

## 3. UI/UX — 없음(백엔드 랭킹 정확도).

## 4. Logic
- `ranking.py`: `_TickerState.news: dict[str, datetime]`. `ingest_news(ticker, source_url, ts)` — `news[source_url] = ts`(중복 자동 제거·최신 갱신). `_metrics`: `news_count = sum(1 for ts in st.news.values() if ts >= since)`.
- `worker.py`: `research.ingested` 핸들러가 `ranker.ingest_news(ticker, event["source_url"], ts)`로 호출(source_url 전달).

## 5. File Map
- `[Mod] services/issue-detector/app/ranking.py` — `_TickerState.news` dict화·`ingest_news(source_url)`·`_metrics` 유일 카운트
- `[Mod] services/issue-detector/app/worker.py` — `ingest_news`에 source_url 전달
- `[Mod] services/issue-detector/tests/test_ranking.py` — 중복 제거·회귀 테스트
- `[New] doc/design/issue-detector/api-contract-issue-dedup.py`

## 6. Verification
- 단위: AC1 중복 1카운트 / AC2 다른 url 각각 / AC3 윈도우 / AC4 회귀(score 공식 불변).
- 통합: 재빌드 후 issue.selected score가 정상 범위(수십)로 — 812 같은 폭발 소멸.

## 7. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /design | news_count 중복 제거. §6 실측(score 812=재발행 중복). `_TickerState.news` dict(source_url→ts), `ingest_news`에 source_url, 유일 카운트. 공식·임계 불변. 계약 mypy 통과. ADR 불요(버그 수정). 발행측 재발행은 ㉝에서 별도. |
