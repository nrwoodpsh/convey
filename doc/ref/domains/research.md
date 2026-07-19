# research (리서치 소스)

- **책임**: 시세·뉴스를 **종목·사건별로 구조화** 저장(관계·인과 그래프 + 사실) + 출처/라이선스. `market-feed`(KIS 시세)·`news-feed`(뉴스·RSS + 종목·사건 태깅) 워커가 수집하고, `research`가 저장해 근거 데이터·RAG(GraphRAG+SQL)를 제공. **금융 도메인** — 알파1(근거·정확)의 심장.
- **지식 저장(하이브리드)**: **Neo4j**(노드 Stock·Event·Sector, 엣지 AFFECTS·SUPPLIES·COMPETES = 관계·인과) + **Postgres**(Article·PriceTick 사실). 추출 파이프라인(NER+관계추출)이 그래프를 채움 = 품질 원천.
- **연동**: `content`/`agent`(근거 데이터·`/search` RAG), `issue-detector`(`market.ticks`·`research.ingested` 스트림)
- **이벤트(안)**: 발행 `market.ticks`(market-feed) / `research.ingested`(news-feed, 축적 완료 — 자동 체이닝 없음)
- **경계**: 콘텐츠 생성·초안 ✗ → `content`. 이슈 랭킹 ✗ → `issue-detector`. 외부 채널 발행 ✗ → `publishing`. 모델 추론 ✗ → `llm-inference`/`agent`.
- **구현 위치**: `services/research/`(sample-domain 복제) + `services/news-feed/`(research-feed 개명 완료) + `services/market-feed/`(원형 실사용) + `research_db`(Postgres — 사실) + `research_graph`(Neo4j — round① 추가 예정)

> **저장소**: 관계·인과 = **Neo4j 지식 그래프**(ADR 0005 — 이전 "그래프 미사용" 대체). 사실(시세·기사) = Postgres SQL. **벡터 의미검색(pgvector)은 POC 제외**(ADR 0006 — RAG는 GraphRAG+SQL). LoRA 미사용이라 그래프가 품질의 유일한 레버.
> **가드레일: 원문·기사는 출처 URL·라이선스 메타 필수 동반**(무출처 생성 금지). 텍스트 추론은 로컬 Ollama만.
> 엔티티·스키마는 `/design` 확정. **빌드 ① 우선.**
