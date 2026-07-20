# ADR 0002 — RAG 저장소로 별도 벡터DB 대신 Postgres + pgvector

> **갱신([0004]·[0005]·[0006])**: pgvector는 주력 → 보조([0004]·[0005]) → **POC 제외·보류([0006])**. POC RAG는 **GraphRAG(Neo4j)+SQL 사실조회**로 간다(벡터 없음). 관계형(Postgres)은 시세·기사 등 **사실** 저장으로 계속 유효. 아래 본문은 결정 당시 기록(pgvector 채택) — POC 상태는 [0006]이 정본.

- **상태**: 채택 (2026-07-18) → **[0006]에서 POC 제외(보류)** (2026-07-19)
- **맥락**: CONVEY의 핵심은 "리서치 원문 검색(RAG)"이다. 그러나 원형은 `agent/rag/{retriever,embeddings}.py`가 **스텁**이고, `main.py`에서 `retriever=None`을 주입하며, `docker-compose.yml`에 벡터DB가 없다(pgvector 주석처리). 저장소를 결정해야 한다(설계 문답 Q2).
- **결정**: 별도 벡터DB(Qdrant·Milvus 등)를 도입하지 않고 **기존 Postgres에 pgvector 확장**을 켜서 `research_db`에 임베딩을 저장한다. 임베딩 모델은 로컬 **`nomic-embed-text`(Ollama)**, `vector_top_k=4` 기본. `agent`의 retriever/embeddings 스텁을 pgvector로 배선.
- **트레이드오프**: 초대형 스케일에서 전용 벡터DB 대비 성능 한계 vs 인프라 단순화(운영 컴포넌트 1개 감소)·서비스별 DB 원칙 유지·트랜잭션 일관성. 단일 사용자 규모에 충분.
- **영향**: `research` 도메인이 임베딩 소유, `agent`가 pgvector 검색. `docker-compose.yml` pgvector 주석 해제, `research_db`에 확장 설치 필요.
- **대안(기각)**: 전용 벡터DB — 규모 대비 운영 과함. 인메모리 검색 — 영속성·재기동 문제.
- **관련**: [0001-multimedia-pipeline-pivot]. `doc/ref/domains/01.research.md`, `doc/ref/architecture/README.md` 반영.
