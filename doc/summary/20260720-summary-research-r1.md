# 20260720 — 요약: research 라운드① (진행 중)

- **Task**: `doc/design/research/task-research-20260720.md` (ADR 0004·0005·0006)
- **작업**: /run(builder) · 날짜 2026-07-20 · 브랜치 main · **로컬 전용**(님 PG·Neo4j·Ollama)
- **상태**: 알파 코어(하이브리드 추출·그래프·사실) 실서비스 검증. consumer·`/search` 통합 남음.

## 개요

시세·뉴스를 관계·인과 그래프(Neo4j) + 사실(Postgres)로 저장하는 research 도메인의 코어를 구현했다. 하이브리드 추출(규칙 태깅 + LLM 관계추출)과 그래프·사실 저장을 **실제 로컬 스택으로 검증**했다.

## 변경사항 (BE)

- `services/news-feed/app/tagging.py` — 규칙/사전 종목·사건 태깅(환각 0)
- `services/research/app/extract/relations.py` — LLM 관계추출 + 환각 필터(허용 엔티티·엣지만)
- `services/research/app/graph/neo4j_repo.py` — 노드/엣지 upsert(source_article_id 결속) + 1홉 traversal
- `services/research/app/domains/research/models.py` — `Article`·`PriceTick`(출처·라이선스 필수)
- `services/research/app/domains/research/repository.py` — `fact_search`·`source_urls_for`(SQL, 출처 동반)
- `services/research/app/domains/research/{schemas,service,router}.py` — `GET /research/search` GraphRAG 통합(그래프 관계 + SQL 사실 → SearchResponse)
- `services/research/app/main.py`·`config.py` — Neo4j 드라이버 배선
- `docker-compose.yml`·`.env.example` — Neo4j 전용 컨테이너·`NEO4J_*`

## DB

- 네이티브 PG(localhost)에 `research_db`·`content_db` + `app` role 생성(님 gaia_cmis·greed 옆)
- Neo4j 전용 컨테이너 기동(7474/7687, 볼륨 neo4jdata)

## 검증 (전부 실서비스·로컬)

- 규칙 태깅 단위 5 · LLM 필터 단위 4 · 엣지 화이트리스트 단위 1 — pass, mypy --strict clean
- **실 Ollama qwen3:14b**: 기사→관계 추출("삼성전자-COMPETES->SK하이닉스" 등)
- **실 Neo4j**: upsert→traversal, 근거 id 동반 확인
- **실 research_db**: fact_search 매칭·출처 동반·무관 제외
- **실 PG+Neo4j**: `/research/search` 조립 — facts(사실)+relations(관계) **모두 출처 동반**(GraphRAG)

## 특이사항 (남은 작업·후속)

- **남음**: research consumer(`research.ingested` Kafka 소비 → 태깅+추출+저장 파이프라인) — Kafka 컨테이너 기동 필요. (`/search` 통합·그래프·사실은 완료)
- **후속**: 그래프 노드가 현재 generic `Entity` — 타입 노드(Stock/Sector/Company)와 티커 사전 연계는 후속. news-feed/market-feed 실수집(KIS·RSS)도 후속.
- 커밋: 슬라이스별로 진행(`ea6fbbe`·`3d1fa47`·`9b0ab57` + 이번 Postgres 사실 레이어).
