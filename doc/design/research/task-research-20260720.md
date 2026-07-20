# task-research-20260720.md

> 라운드 ① (데이터 기반). 알파1(근거·정확)의 심장. 계약 정본 = `api-contract.py`. 여기엔 자연어 설계만.

## 1. Requirements

- **Scenario**: `market-feed`(KIS 시세)·`news-feed`(뉴스·RSS)가 원천을 수집한다. `research`가 이를 **관계·인과 그래프(Neo4j) + 사실(Postgres)**로 저장하고, `agent`가 `GET /research/search`로 근거를 회수한다.
- **Objective**: 종목·사건의 관계·인과를 그래프로 축적하고, 출처에 결속된 사실을 SQL로 저장해, **환각 없는 근거 데이터**를 콘텐츠 제작에 공급한다.
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract.py`가 contract-gate(`mypy --strict`) 통과 (그래프 타입·사실·`/search`·이벤트 포함) — ✅
  - [ ] AC2: 그래프 노드 4종·엣지 5종이 **방향·속성·카디널리티**와 "어떤 사실에서 유도되는지" 매핑을 가짐
  - [ ] AC3: `/research/search` 결과의 **모든 fact·relation이 `source_url` 동반**(무출처 0건 — 가드레일)
  - [ ] AC4: 추출 파이프라인이 **하이브리드**(종목 태깅=규칙/사전, 관계추출=로컬 LLM)로 정의되고, 관계는 근거 기사(`source_article_id`)에 결속
  - [ ] AC5: `Article`·`PriceTick` 스키마와 그래프 노드의 **ID 연결 규칙** 정의 (벡터 없음)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대(부딪히면 배울 함정)**:
  - `research` 모델은 현재 자리표시(`Article` 최소 컬럼)뿐. `docker-compose`에 **Neo4j 컨테이너 없음** — round① 신규 배선 필요.
  - `research.ingested` 소비자가 아직 없음(`research`는 API만). news-feed 발행 → research가 **소비 루프**(content consumer 패턴 재사용)로 받아 그래프를 채워야 함.
  - LLM 관계추출은 **환각 위험의 진입점**. 추출된 엔티티가 태깅된 종목/기사에 근거 없으면 버려야 함(아래 결정 2).
  - `sub`/식별자: 그래프 노드↔Postgres 사실 연결 키를 처음부터 고정하지 않으면 나중에 재작업(ADR 0005의 경고).
- **핵심 결정**(택한 안 + 기각한 대안):
  - **결정 1 — 추출 방식**: 택함 = **하이브리드**(종목·엔티티 태깅 = 규칙/사전 → 결정론·환각0 / 관계추출 = 로컬 LLM Ollama) / 기각 = 규칙 전용(관계 커버리지 좁음)·LLM 전용(엔티티까지 환각) / 사유 = 정확성(알파)과 커버리지의 균형
  - **결정 2 — 환각 방지**: 택함 = **관계는 반드시 근거 기사에 결속**(`source_article_id`), LLM이 새 수치·엔티티를 만들면 폐기(태깅된 종목/기사 범위 밖 엔티티 drop) / 기각 = LLM 출력 신뢰 / 사유 = "안 틀리는 금융 콘텐츠"
  - **결정 3 — 그래프↔사실 연결**: 택함 = **Postgres가 사실 정본, 그래프는 참조**(엣지 속성에 `source_article_id`, `Stock.ticker`↔`PriceTick.ticker`) / 기각 = 그래프에 사실 복제 / 사유 = 시세 시계열·원문은 Postgres가 적합(ADR 0005)
  - **결정 4 — 수집 실구현 범위**: 택함 = **이번 라운드는 계약·스키마·파이프라인 설계 + 소비 배선까지**, 실제 KIS·RSS 크롤링은 `/builder`에서 스텁→실연동 / 기각 = 지금 전부 실연동 / 사유 = 설계 안정화 우선

## 3. UI/UX

해당 없음 (API 전용 BE).

## 4. Logic

**그래프 모델 (Neo4j research_graph)**
- 노드: `Stock`{ticker(unique)·name·sector} · `Event`{id·type(실적/공시/급등락)·date·summary} · `Sector`{name(unique)} · `Company`{name·kind(company|person)}
- 엣지(방향): `Stock-[:HAS_EVENT]->Event` · `Event-[:AFFECTS]->Stock`(인과) · `Company-[:SUPPLIES]->Company` · `Stock-[:COMPETES]->Stock` · `Stock-[:BELONGS_TO]->Sector`
- 모든 엣지 속성: `source_article_id`·`created_at` (근거·감사)

**추출 파이프라인 (하이브리드)**
1. `news-feed`: 수집 → **규칙/사전 종목 태깅**(ticker 사전 매칭) + 사건 후보 힌트 → `research.ingested` 발행 (원문·출처·라이선스 포함)
2. `research` 소비: `research.ingested` 수신 →
   - **사실 저장**: `Article`(Postgres) + 출처/라이선스 (필수)
   - **관계추출**: 로컬 LLM(Ollama)에 [기사 + 태깅 종목] → `(subject, edge, object)` 후보. 각 후보는 근거 기사에 결속. **태깅/기사 범위 밖 엔티티·수치는 폐기**(환각 방지)
   - **그래프 upsert**: 노드·엣지 생성, 엣지에 `source_article_id`
3. `market-feed`: KIS 시세 → `market.ticks` → `research`가 `PriceTick` 저장

**`/research/search` (GraphRAG)**
1. `q`/`ticker` → 종목 노드 해석(없으면 `ENTITY_NOT_FOUND`)
2. `hops`만큼 그래프 traversal → 관계 사슬 → `RelationHit`(근거 기사·URL 동반)
3. Postgres에서 사실 회수(`Article`·`PriceTick`, `window_days`) → `FactHit`(출처 동반)
4. `SearchRes` 조합. **무출처 항목은 반환하지 않음.**

## 5. Implementation Split

- **BE(research)**: 그래프/사실 저장, 소비 루프, `/search`. **FE 없음.**

## 6. File Map (기계적)

- `[New] doc/design/research/api-contract.py` — 계약 (작성 완료·mypy 통과)
- `[Mod] services/research/app/domains/research/models.py` — `Article`·`PriceTick` 확정 (Postgres)
- `[New] services/research/app/graph/` — Neo4j 드라이버·Cypher(노드/엣지 upsert·traversal)
- `[New] services/research/app/consumer.py` — `research.ingested` 소비 → 사실 저장 + 관계추출 + 그래프 upsert
- `[New] services/research/app/extract/` — 관계추출(로컬 LLM 호출 + 근거 결속·환각 필터)
- `[Mod] services/research/app/domains/research/{repository,service,schemas,router}.py` — `/search`를 GraphRAG(그래프+SQL)로 구현
- `[Mod] services/news-feed/app/` — 규칙/사전 종목 태깅 + `research.ingested` 페이로드
- `[Mod] services/market-feed/app/` — `market.ticks` 페이로드(계약 정합)
- `[Mod] docker-compose.yml` — **Neo4j 컨테이너 추가**, research `depends_on` 조정, `NEO4J_URL` 환경
- `[Mod] infra/db/init/01-create-databases.sql` — `research_db` 유지(벡터 확장 없음)
- `[Mod] .env.example` — `NEO4J_URL`·`NEO4J_AUTH`, KIS·RSS 키

## 7. Verification

- 계약: `python -m mypy --strict --ignore-missing-imports doc/design/research/api-contract.py` → Exit 0 (AC1) ✅
- 구현 후(`/builder` tdd-verify):
  - 기사 1건 투입 → `Article` 저장 + 그래프 엣지 생성, 엣지에 `source_article_id` 존재 (AC4)
  - `/search` 응답의 모든 fact·relation에 `source_url` 존재 (AC3)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260720 | /design | 최초 설계 — 하이브리드 추출·GraphRAG·2-store (ADR 0004·0005·0006) |
| 20260720 | /builder | 규칙 태깅·LLM 관계추출(**실 Ollama qwen3:14b**)·GraphRepo(**실 Neo4j** 라운드트립) 구현+검증. compose에 Neo4j 전용 컨테이너 추가, 네이티브 PG에 research_db/content_db 생성. 노드는 현재 generic `Entity`(타입 노드 Stock/Sector는 후속) |
| 20260720 | /builder | Postgres 사실 모델(Article·PriceTick) + `fact_search` 구현. **실 research_db 라운드트립 검증**(매칭·출처 동반·무관 제외 — AC3·AC5). |
| 20260720 | /builder | `GET /research/search` GraphRAG 통합 — `service.search`가 GraphRepo(Neo4j 관계) + `fact_search`(SQL 사실) 조립 → `SearchResponse`(FactHit·RelationHit, 계약 정합). main에 Neo4j 드라이버. **실 PG+Neo4j 조립 검증**(facts·relations **모두 source_url 동반** — AC3). mypy clean. |
| 20260720 | /builder | research consumer — `handle_ingested`(이벤트→Article 저장+LLM 관계추출+그래프 upsert) **실 PG+Neo4j+Ollama 검증**(이벤트 1건→article#3+관계 2). `run_consumer`(Kafka 루프+llm-inference) 배선, main 백그라운드 등록. Kafka 기동. **라운드① 코어 완료.** |
| 20260720 | /builder · Deviation | 계약 `ResearchIngestedEvent`: `article_id` → **`title·body·entities`**로 정합. 사유: 원문 없으면 research가 Article 저장·추출 불가 / 태깅은 코드(005930)인데 추출은 이름(삼성전자) 필요 → `entities`(이름) 추가. contract-gate 통과. **전송 계층**(Kafka 루프·llm-inference HMAC)은 표준 배선이나 **e2e 미검증**(Kafka 호스트노출·llm-inference 컨테이너 필요). 노드는 generic `Entity`(타입노드 후속) |
