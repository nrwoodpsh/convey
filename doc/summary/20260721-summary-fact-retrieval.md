# 20260721 — 요약: 뉴스 근거 회수 개선 (종목 태깅 기반)

- **Task**: `doc/design/research/task-fact-retrieval-20260721.md` (라운드⑧, ADR 0008)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 research_db·전 스택 e2e)
- **상태**: 전 스택 e2e에서 드러난 "뉴스 인용 0" 약점 해소. 종목 기준 정확 회수로 fact가 스크립트에 붙음.

## 개요

종목으로 생성해도 스크립트에 뉴스 근거가 안 붙던 문제를 고쳤다. 원인은 ① `Article`이 태깅된 종목을 저장 안 함, ② `fact_search`가 검색어 전체를 통째 ILIKE. `Article.tickers`(JSONB)를 영속하고, `ticker`가 있으면 **종목 태깅 기사를 정확히 회수**(검색어 문자열과 무관)하도록 바꿨다.

## 변경사항 (BE, research)

- `domains/research/models.py` — `Article.tickers`(JSONB, 기본 `[]`)
- `consumer.py` — `handle_ingested`가 태깅 `tickers` 영속
- `domains/research/repository.py` — `fact_search_by_ticker`(`tickers @> [ticker]`)
- `domains/research/service.py` — `ticker` 있으면 종목 기사 우선 + 키워드 보충(id dedup, top_k)
- `alembic/versions/bbba385fe7b9_article_tickers.py` — `articles.tickers` 추가(`2dea57e84dfe` 다음)

## API/계약 변경

- 없음(회수 정확도만 개선, `SearchRes`·`FactHit` 불변).

## DB

- research_db `articles.tickers`(JSONB NOT NULL DEFAULT `[]`) — Alembic `bbba385fe7b9` **적용됨**(head).
- 기존 행은 `[]`(백필 없음) — 종목 회수는 신규 ingest부터.

## 검증 (실 research_db·전 스택)

- **AC2**: 005930 태깅 기사 ingest → `Article.tickers=['005930']` 저장.
- **AC3**: 검색어 `'삼성전자 이슈'`(제목 무매칭)로도 `service.search(ticker='005930')`가 그 기사 회수, 무출처 0.
- **AC5**: 키워드 `fact_search` 결과 동일(회귀 0).
- **AC4 (전 스택)**: `generate(005930)` → 스크립트 섹션 `hook·chart·fact·macro`, citations 7(시세 1 + 뉴스 1 + 거시 5), 출처 도메인에 news 등장(이전 fact 0 → ≥1) → mp4 h264 1080×1920 ready.
- mypy --strict clean.

## 특이사항 (이탈·후속)

- **이탈(수정)**: `service.search`에서 fact 루프 변수 `row`가 가격 블록 `row`(latest_price)와 mypy 상 충돌 → `fr`로 정정.
- 저장 형태는 JSONB 배열 + `@>`(POC). 다중 종목·대량 조회가 무거워지면 정규화 테이블·GIN 인덱스 후속.
- **후속**: 종목명 사전(TICKER_DICT)이 news-feed·(암묵) research 양쪽에 필요 — 공유 위치 검토. 거시 종목 연관 필터.
- 커밋: 아직(사람 게이트 — `/commit`).
