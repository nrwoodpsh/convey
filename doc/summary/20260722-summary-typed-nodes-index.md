# 20260722 — 요약: Stock 타입 노드 + JSONB GIN 인덱스 (B5)

- **Task**: `doc/design/research/task-typed-nodes-index-20260722.md` (라운드⑲, 정제)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 Neo4j·research_db)
- **상태**: 그래프 종목 노드 구분(:Stock) + 종목 기사 조회 인덱스. 5개 AC 충족. B(정제) 완료.

## 개요

generic `:Entity` 노드에 **알려진 종목명은 `:Stock` 라벨 + `ticker` 속성**을 붙여 종목을 구분·PriceTick과 연계(ADR 0005). `articles.tickers @>` 조회에 **JSONB GIN 인덱스**를 추가. 전체 4타입(Event/Sector/Company) 분류는 위험·범위로 후속.

## 변경사항

- `services/research/app/graph/neo4j_repo.py` — `_STOCK_BY_NAME`(종목명→티커) + `_label_stock`(`MATCH ... SET n:Stock, n.ticker=`) + upsert에서 subject·object 라벨링. 기존 `:Entity` 유지(멀티라벨).
- `services/research/alembic/versions/57e61ba69037_articles_tickers_gin_index.py` — `articles.tickers` **GIN 인덱스**(`bbba385fe7b9` 다음, 실 research_db 적용).

## API/계약 변경
- 없음.

## 검증 (실 Neo4j·research_db·로컬)

- **AC2**: 삼성전자·SK하이닉스 upsert → labels `[Entity, Stock]` + ticker(005930/000660). 미지 엔티티(젠슨황) → `[Entity]`만.
- **AC3**: `relations_of("삼성전자")` 정상 회수(Stock도 :Entity라 기존 traversal 유지).
- **AC4**: temp+실 research_db `upgrade head` → `ix_articles_tickers`(gin) 생성, 버전 `57e61ba69037`.
- **AC5**: mypy --strict clean, research 단위 5 회귀 없음.

## 특이사항 (후속)

- **범위**: Stock 라벨만(사전 기반·결정론·저위험). **Event/Sector/Company 타입 분류**(LLM/규칙)와 `Stock.ticker↔PriceTick` 조인 회수 활용은 후속(추출·회수 재설계 필요).
- name→ticker 사전이 news-feed `TICKER_DICT`·content `_BROLL_MAP`과 분산 — 공유 위치 통합 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
