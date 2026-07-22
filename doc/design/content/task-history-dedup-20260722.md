# task-history-dedup-20260722.md

> 라운드 ⑭ (A2 — 콘텐츠 히스토리 조회 + 자동 양산 중복회피). 알파4(양산). ADR 0006.
> 계약 변경 없음(기존 SearchHit/SearchResponse). 자연어 설계만.

## 1. Requirements

- **결론**: `history_search`가 스텁(NotImplementedError)이고 `/content/search`는 빈 목록만 준다. 자동 양산(A1)이 **같은 종목을 반복 생성**할 수 있다(재기동·주기마다). 히스토리 조회를 구현하고, **자동 경로에 중복회피**를 붙여 A1의 짝을 완성한다.
- **Scenario**: (1) agent/사람이 `GET /content/search?q=...`로 과거 콘텐츠를 조회. (2) 자동 양산이 이슈를 받을 때 **같은 종목 최근 콘텐츠가 있으면 건너뛴다**.
- **Objective**: 중복 콘텐츠 양산 방지(알파4 품질). 벡터 아님(키워드/메타, ADR 0006).
- **Acceptance Criteria**:
  - [ ] AC1: 변경 파일 `mypy --strict` 통과(계약 변경 없음)
  - [ ] AC2: `repository.history_search` 구현(스텁 제거) — 최근 콘텐츠를 키워드로 조회, `(content_id, text)` 반환
  - [ ] AC3: `GET /content/search`가 매칭 콘텐츠 반환(무매칭 시 빈 목록, 에러 아님)
  - [ ] AC4: 자동 양산(`handle_issue`)이 **같은 ticker 최근(window) 활성/완료 잡이 있으면 생성 skip**(중복 잡 0)
  - [ ] AC5: **수동** `POST /content/generate`는 중복회피 미적용(명시 의도 — 항상 생성). 회귀 없음

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - "콘텐츠 있음"의 정의: `Content`가 있는(=ready/approved) 잡만? 아니면 진행 중(scripting/assembling)도 중복으로 볼까 — **재기동 직후 in-memory 랭킹 초기화로 재발행**되는 걸 막으려면 진행 중도 포함해야.
  - 실패(failed) 잡은 중복으로 보면 안 됨(재시도 허용).
  - 수동 POST에 dedup 걸면 사용자가 강제 재생성 못 함 → 자동만 적용.
  - history_search 키워드는 Korean topic ILIKE(벡터 아님).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 중복 기준**: 택함 = **같은 ticker + 최근 window(기본 1일) + status ≠ failed** 잡 존재 시 중복 / 기각 = ready/approved만(진행 중 재발행 못 막음)·topic 문자열 매칭(종목이 더 정확) / 사유 = 자동 루프의 반복 발행을 확실히 억제.
  - **결정 2 — 적용 위치**: 택함 = **자동 경로(`handle_issue`)만** dedup, 수동 POST는 무조건 생성 / 기각 = 공통 적용(수동 강제 재생성 막힘) / 사유 = 자동=스팸 방지, 수동=명시 의도.
  - **결정 3 — history_search 구현**: 택함 = **`GenerationJob` topic ILIKE + `Content` 조인**(완성본 있는 것), 최신순 top_k, `(content_id, text=topic)` / 기각 = 벡터 유사도(ADR 0006 제외) / 사유 = 키워드/메타로 충분(POC).

## 3. UI/UX
해당 없음.

## 4. Logic

```
repository.history_search(session, query, top_k):
  SELECT c.id, j.topic FROM contents c JOIN generation_jobs j ON c.job_id=j.id
   WHERE j.topic ILIKE %query% ORDER BY c.created_at DESC LIMIT top_k
  → [(content_id, topic)]

repository.recent_ticker_job(session, ticker, window_days):
  SELECT 1 FROM generation_jobs
   WHERE ticker=:ticker AND status != 'failed' AND created_at >= now()-window LIMIT 1
  → bool

service.search_history: history_search → SearchResponse(hits=[SearchHit(content_id, text, score=1.0)])

consumer.handle_issue:
  if recent_ticker_job(ticker, window): log·skip   # 자동 중복회피
  else: start_generation(...)                        # 기존
```

## 5. Implementation Split (다음 /builder)

- **BE(content)**: `repository.history_search`(구현) + `repository.recent_ticker_job`(신규). `service.search_history`가 history_search 사용. `consumer.handle_issue`에 dedup 가드. `config`에 `dedup_window_days`.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/content/app/domains/content/repository.py` — `history_search` 구현 + `recent_ticker_job`
- `[Mod] services/content/app/domains/content/service.py` — `search_history`가 repository 호출
- `[Mod] services/content/app/consumer.py` — `handle_issue` dedup 가드
- `[Mod] services/content/app/config.py` — `dedup_window_days`

## 7. Verification (다음 /builder)

- 계약 변경 없음 → mypy (AC1)
- 실 content_db: Content 하나 넣고 `history_search(topic 키워드)` → 그 content_id 반환(AC2), 무매칭 → 빈 목록(AC3)
- `recent_ticker_job`: 최근 활성 잡 있는 ticker → True(skip), 없으면 False. `handle_issue` 두 번 호출 시 두 번째는 skip(중복 잡 0)(AC4)
- 수동 `start_generation` 두 번 → 둘 다 잡 생성(dedup 미적용, AC5)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 히스토리 조회 구현 + 자동 양산 중복회피(handle_issue). 중복=같은 ticker·최근 window·non-failed. 수동은 미적용. A1의 짝(중복 스팸 방지). 벡터 아님. |
| 20260722 | /builder | `repository.history_search` 구현(contents⨝generation_jobs topic ILIKE, 스텁 제거) + `recent_ticker_job`(ticker·window·non-failed 판정). `service.search_history`가 실제 조회 → SearchHit. `consumer.handle_issue`에 dedup 가드. config `dedup_window_days=1`. **검증(실 content_db·Kafka)**: history_search 매칭 반환·무매칭 빈목록(AC2·AC3), recent_ticker_job 판정, **자동 handle_issue 2회→1건(중복회피, AC4)**, 수동 start_generation 2회→2건(dedup 미적용, AC5). mypy clean. 계약·마이그레이션 변경 없음. |
