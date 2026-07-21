# task-fact-retrieval-20260721.md

> 라운드 ⑧ (뉴스 근거 회수 개선). 알파1(근거·정확). ADR 0008.
> 계약 변경 없음(내부 회수 로직). 자연어 설계만.

## 1. Requirements

- **결론**: 전 스택 e2e에서 드러난 약점 — 종목으로 생성해도 **뉴스(fact) 인용이 0**이었다. 원인 둘: ① `Article`이 태깅된 `tickers`를 저장하지 않아 "이 종목 기사"를 못 찾음, ② `fact_search`가 검색어 전체(`"삼성전자 이슈"`)를 통째 ILIKE라 매칭 실패. 종목 기준으로 기사를 정확히 회수하게 고친다.
- **Scenario**: agent가 `GET /research/search?ticker=005930` 하면, **005930으로 태깅된 기사**들이 facts로 회수된다(검색어 문자열과 무관하게). 스크립트에 뉴스 근거가 인용된다.
- **Objective**: 종목 뉴스 근거가 스크립트에 확실히 붙게 — 소스 확장(라운드⑥)의 가치를 파이프라인 끝까지 전달. 출처 동반(무출처 0).
- **Acceptance Criteria**:
  - [ ] AC1: 변경 파일 `mypy --strict` 통과(계약 변경 없음)
  - [ ] AC2: 새 ingest `Article`에 태깅 `tickers` 저장(005930 태깅 기사 → `tickers`에 `005930`)
  - [ ] AC3: `GET /research/search?ticker=005930` → **005930 태깅 기사**가 facts에 포함(검색어 문자열 무매칭이어도), 전부 `source_url` 동반
  - [ ] AC4: e2e `POST /content/generate`(005930) 스크립트 citations에 **뉴스(fact) 출처 ≥1** 포함(이전 0)
  - [ ] AC5: 무출처 0 유지, 기존 키워드 `fact_search` 회귀 없음

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **기존 Article 백필 없음**: `tickers` 컬럼 추가 시 과거 행은 `[]` — 종목 회수 안 됨. 신규 ingest부터. e2e는 재수집 필요.
  - Alembic: `articles.tickers` 추가 마이그레이션(리비전 `2dea57e84dfe` 다음).
  - JSON 배열 컨테인먼트 쿼리는 **JSONB**라야 인덱스·`@>` 연산 가능(JSON은 텍스트).
  - `handle_ingested`는 `market.ticks`·`research.macro`와 무관 — Article 경로만.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 종목 회수 방식**: 택함 = **`Article.tickers` 영속(JSONB) + 종목 컨테인먼트 조회** / 기각 = ticker→종목명 사전으로 이름 ILIKE(Option B) / 사유 = 정확·재사용(issue-detector·content도 씀)·이름 표기 흔들림 무관. B는 사전 중복·이름이 본문에 있어야만 매칭(취약).
  - **결정 2 — 저장 형태**: 택함 = **JSONB 배열 컬럼**(`@>` 컨테인먼트) / 기각 = 정규화 `article_tickers` 조인 테이블 / 사유 = POC 단순. 다중 종목·대량 조회가 무거워지면 후속 정규화.
  - **결정 3 — 회수 조합**: 택함 = **ticker 있으면 종목 기사 우선 + 부족분 키워드로 채움**(id 중복 제거, top_k 한도) / 기각 = ticker 시 종목 전용 / 사유 = 종목 없는 일반 질의도 지원 유지(하위호환).
  - **결정 4 — 계약 영향**: 택함 = **없음**(SearchRes·FactHit 그대로) / 사유 = 회수 정확도만 개선, 응답 형태 불변.

## 3. UI/UX
해당 없음 (API 전용 BE).

## 4. Logic

**저장 (research consumer)**
```
handle_ingested: Article(..., tickers=event.get("tickers", []))   # 태깅 종목 영속
```

**회수 (research service.search)**
```
if ticker:
   ticker_facts = repository.fact_search_by_ticker(session, ticker, top_k, window_days)  # tickers @> [ticker]
   kw_facts     = repository.fact_search(session, query, top_k, window_days)             # 기존 키워드
   facts = dedup_by_id(ticker_facts + kw_facts)[:top_k]                                  # 종목 우선
else:
   facts = repository.fact_search(session, query, top_k, window_days)
facts = [f for f in facts if f.source_url]   # 무출처 제거(가드레일)
```
- `fact_search_by_ticker`: `SELECT id,title,source_url FROM articles WHERE tickers @> :one ORDER BY published_at DESC LIMIT n` (`:one = [ticker]`, JSONB).

## 5. Implementation Split (다음 /builder)

- **BE(research)**: `models.Article.tickers`(JSONB, 기본 `[]`). `consumer.handle_ingested` tickers 저장. `repository.fact_search_by_ticker` + `service.search` 조합. Alembic 마이그레이션(articles.tickers 추가).
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/research/app/domains/research/models.py` — `Article.tickers`(JSONB)
- `[New] services/research/alembic/versions/{rev}_article_tickers.py` — 컬럼 추가(리비전 `2dea57e84dfe` 다음)
- `[Mod] services/research/app/consumer.py` — `handle_ingested`가 tickers 저장
- `[Mod] services/research/app/domains/research/repository.py` — `fact_search_by_ticker`
- `[Mod] services/research/app/domains/research/service.py` — ticker 회수 조합(종목 우선 + 키워드 보충, dedup)

## 7. Verification (다음 /builder)

- 계약 변경 없음 → `mypy --strict` 변경 파일 (AC1)
- 구현 후(실 research_db):
  - 005930 태깅 기사 ingest → `Article.tickers` 저장 확인(AC2)
  - `service.search(ticker=005930)` → 005930 기사 facts 포함, 검색어 무매칭 상황에서도(AC3), 무출처 0(AC5)
  - 기존 키워드 fact_search 결과 동일(회귀 0, AC5)
  - (전 스택) generate(005930) → 스크립트 citations에 뉴스 출처 ≥1(AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | 뉴스 회수 개선 — `Article.tickers`(JSONB) 영속 + 종목 컨테인먼트 회수(종목 우선+키워드 보충). 계약 불변. e2e에서 fact 인용 0 문제 해결 목표. |
| 20260721 | /builder | `Article.tickers`(JSONB, `@>` 회수) + `handle_ingested` 저장 + `fact_search_by_ticker` + `service.search` 조합(종목 우선+키워드 dedup). Alembic `bbba385fe7b9`(articles.tickers, `2dea57e84dfe` 다음, **실 research_db 적용**). **실 research_db 검증**: 005930 태깅 기사 → tickers 저장(AC2), 검색어 무매칭이어도 종목 회수(AC3), 키워드 회귀 없음(AC5). **전 스택 e2e**: generate(005930)→스크립트 섹션 `hook·chart·fact·macro`, citations 7(시세·뉴스·거시 5), 출처에 news 등장(fact 인용 0→≥1, AC4)→mp4 ready. mypy clean. 이탈: 변수명 `row` 충돌(fact 루프 vs latest_price)→`fr`로 정정. |
