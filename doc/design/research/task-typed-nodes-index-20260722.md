# task-typed-nodes-index-20260722.md

> 라운드 ⑲ (B5 — 타입 그래프 노드 + JSONB GIN 인덱스). 정제. ADR 0005·0006.
> 계약 변경 없음. 자연어 설계만.

## 1. Requirements

- **결론**: (1) Neo4j 노드가 전부 generic `:Entity`라 종목을 구분·연계 못 함 → **알려진 티커명 노드에 `:Stock` 라벨 + `ticker` 속성**을 붙여 PriceTick과 연계(ADR 0005 결정3). (2) `articles.tickers @>` 조회에 인덱스가 없음 → **JSONB GIN 인덱스**로 가속. **전체 4타입(Event/Sector/Company) 분류는 위험·범위 커 후속**.
- **Objective**: 종목 노드 구분(알파 정밀도 초석) + 종목 기사 조회 성능. 저위험·결정론(사전 기반, 환각0).
- **Acceptance Criteria**:
  - [ ] AC1: 변경 파일 `mypy --strict` + 마이그레이션 문법 OK
  - [ ] AC2: 그래프 upsert 시 **알려진 티커명 노드 → `:Stock` 라벨 + `ticker` 속성**(실 Neo4j), 미지명은 generic `:Entity` 유지
  - [ ] AC3: 기존 `relations_of` traversal **여전히 동작**(라벨 추가가 회수 안 깨뜨림)
  - [ ] AC4: `articles.tickers` **GIN 인덱스 생성**(마이그레이션 head), `fact_search_by_ticker` 정상
  - [ ] AC5: 기존 그래프 라운드트립·단위 회귀 없음

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - 노드는 `:Entity`(name)로 MERGE됨 — `:Stock` 추가 라벨은 **기존 `:Entity` 유지 위에 덧붙임**(멀티라벨). `relations_of`의 `(s:Entity)` MATCH가 계속 매칭돼야.
  - name→ticker 매핑 필요(research엔 없음, news-feed `TICKER_DICT`와 별개) → 소규모 사전 복제(POC).
  - 전체 타입 분류(Event/Sector/Company)는 LLM/규칙 정확도 리스크·추출·회수 전반 변경 → **이번 범위 제외**.
  - GIN 인덱스: 기존 행 있어도 `CREATE INDEX`는 안전(재구축).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 타입 범위**: 택함 = **Stock 라벨만**(사전 기반, 저위험·고가치) / 기각 = Stock/Event/Sector/Company 전체(정확도 리스크·범위 큼) / 사유 = 종목이 알파(종목 중심)에 가장 값어치, 결정론. 전체는 후속.
  - **결정 2 — 라벨 방식**: 택함 = 기존 `:Entity` **유지 + `:Stock` 덧붙임**(멀티라벨) + `ticker` 속성 / 기각 = `:Entity`→`:Stock` 교체(기존 traversal 깨짐) / 사유 = 하위호환.
  - **결정 3 — 인덱스**: 택함 = **JSONB GIN**(`tickers` 컨테인먼트 가속) / 기각 = 인덱스 없음(대량 시 느림) / 사유 = `@>` 조회 성능.
  - **결정 4 — 매핑 위치**: 택함 = research graph에 소규모 name→ticker 사전 / 기각 = news-feed 사전 공유(경계 복잡) / 사유 = POC 규모, 후속 통합.

## 3. UI/UX
해당 없음.

## 4. Logic

```
neo4j_repo.upsert_relation(s, edge, o, aid):
  기존 MERGE (s:Entity{name})·(o:Entity{name}) + 엣지  (그대로)
  + s/o 이름이 사전에 있으면: SET n:Stock, n.ticker=<ticker>   # Stock 라벨·속성
_STOCK_BY_NAME = {"삼성전자":"005930", ...}  # research graph 소규모 사전

Alembic: CREATE INDEX ix_articles_tickers ON articles USING gin (tickers)
```
- `relations_of`는 `(s:Entity)` 그대로 — Stock도 Entity라 매칭 유지.

## 5. Implementation Split (다음 /builder)

- **BE(research)**: `graph/neo4j_repo.py` upsert에 Stock 라벨·ticker 세팅 + name→ticker 사전. Alembic 마이그레이션(articles.tickers GIN).
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/research/app/graph/neo4j_repo.py` — Stock 라벨·ticker + `_STOCK_BY_NAME`
- `[New] services/research/alembic/versions/{rev}_articles_tickers_gin.py` — GIN 인덱스(`bbba385fe7b9` 다음)

## 7. Verification (다음 /builder)

- 실 Neo4j: "삼성전자" 관계 upsert → 노드에 `:Stock` 라벨·`ticker="005930"`, 미지명은 `:Entity`만(AC2). `relations_of("삼성전자")` 정상 회수(AC3).
- 마이그레이션 upgrade head → `ix_articles_tickers`(gin) 존재, `fact_search_by_ticker` 정상(AC4).
- mypy + 그래프 단위 회귀(AC5).

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | Stock 타입 라벨(사전 기반·멀티라벨·ticker 속성) + articles.tickers JSONB GIN 인덱스. 전체 4타입 분류는 위험·범위로 후속. 저위험 정제. |
| 20260722 | /builder | `neo4j_repo`에 `_label_stock`(알려진 종목명→`:Stock` 라벨+`ticker`, `_STOCK_BY_NAME` 사전) — upsert 시 subject·object 라벨링. Alembic `57e61ba69037`(articles.tickers **GIN**, `bbba385fe7b9` 다음, 실 research_db 적용). **검증**: 실 Neo4j 삼성전자·SK하이닉스 `[Entity,Stock]`+ticker·젠슨황 `[Entity]`만(AC2), relations_of 정상(AC3), temp+실 DB GIN 인덱스 생성·head(AC4), mypy·단위 5 회귀 없음(AC5). 전체 4타입(Event/Sector/Company)은 후속. |
