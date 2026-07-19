# ADR 0006 — POC 범위 확정: 벡터(pgvector) 제외 · 영상 합성 경계 · 용어(POC≠알파)

- **상태**: 채택 (2026-07-19) — [0002]의 pgvector, [0004]·[0005]의 "pgvector 보조" 부분을 POC 범위에서 **보류(deferred)**로 갱신
- **맥락**: POC 시나리오를 구체화하며 세 가지가 흐릿했다. ① 지식 레이어를 Neo4j 그래프로 가는데 **pgvector(벡터 임베딩)까지 같이 가는 게 맞나** ② "정확한 수치"를 외부 생성형 영상 모델에 맡겨도 되나 ③ "POC"와 "알파"를 같은 뜻처럼 섞어 씀. 각각을 결정으로 고정한다.

- **결정 1 — 벡터 임베딩(pgvector)은 POC 제외. RAG는 GraphRAG+SQL.**
  - `research`의 2-store(**Neo4j** 관계·인과 + **Postgres** 시세·기사 사실)는 유지. 여기서 Postgres가 필요한 이유는 **시세 시계열·기사 원문**이지 벡터가 아니다(그래프 DB는 시계열·대용량 텍스트에 부적합).
  - **회수(RAG) = 그래프 traversal(Cypher) + SQL 사실조회**. 벡터 유사도 없이도 완전한 RAG(**GraphRAG**)다. `agent↔research /search` 계약은 불변.
  - `content` 히스토리 중복회피는 **키워드/메타(주제·종목·기간)** 조회로. 임베딩 아님.
  - pgvector·`nomic-embed-text`·`vector_top_k`·`Embedding`/`ContentEmbedding` 엔티티는 **후속 라운드로 보류**(테마 퍼지검색이 실제로 필요해지면 재도입).

- **결정 2 — 화면 위 정확한 수치·차트는 우리(`video-assembly`)가 렌더. 생성형 영상은 POC 제외.**
  - 생성형 영상 모델은 화면 텍스트·숫자를 **픽셀로 그리는** 것이라 정확한 종가·등락률·한글 자막을 못 박는다(프레임마다 뭉개짐). "숫자를 프롬프트에 넣으면 맞게 나온다"는 성립하지 않음.
  - 경계: **외부**(커모디티) = 배경 broll·이미지·TTS(음성). **우리**(알파③) = 화면 위 정확 수치·차트를 **결정론적으로 렌더(matplotlib/ffmpeg drawtext) + 최종 합성**. 검증 가능한 정확성이 우리 통제 영역.
  - 숫자가 나오는 두 경로 구분: **TTS 내레이션(오디오)** 속 숫자는 텍스트를 읽는 것이라 외부 안전. **화면 위 픽셀** 숫자만 우리가 박는다.
  - **POC**: 생성형 영상 모델 제외. 배경(스톡 영상/모션) + 정확 차트 애니 + 텍스트 오버레이 + TTS = 100% 정확·저복잡도. 생성형 영상은 후속 커모디티로 얇게.

- **결정 3 — 용어: POC/MVP(범위) ≠ 알파(차별점).**
  - **알파** = 무엇으로 차별화하나(정확·선별·렌더·양산, [0004]). **POC/MVP** = 처음 최소로 만들어 증명하는 범위. 알파는 그 범위 안에 박힌 알맹이. 서로 다른 축이므로 혼용 금지.
  - 부수: 문서 용어 "배선"은 층위 분리 — **서비스 간 = 연동/연결**, **서비스 내부 의존성 = 주입(DI)/조립**.

- **트레이드오프**: 테마 의미검색(엔티티명을 모를 때의 퍼지검색)을 POC에서 포기 → 대신 관계·사실 정확도에 집중. 필요해지면 pgvector는 Postgres 위에 분리 기능으로 재도입 가능(2-store 구조 불변이라 재작업 작음).

- **영향(코드 반영 완료)**: `docker-compose`(postgres 이미지 plain화), `infra/db/init/02-extensions.sql`(vector 제거), `research`·`content`·`agent` 코드(embedding/vector 제거 → 사실조회·HTTP 근거회수 스텁), pyproject(pgvector·embeddings 의존 제거). 폴더: `research-feed→news-feed` 개명 완료, `llm-trainer` 제거. 문서 `doc/ref/*` 전반 정합.

- **대안(기각)**: pgvector 보조 유지([0005] 원안) — POC 복잡도 대비 효용 낮음. 벡터 완전 삭제(재도입 불가) — 2-store가 유지되므로 굳이 문을 닫을 이유 없어 "보류"로.

- **관련**: [0002-pgvector-rag](벡터 저장소 결정 — 본 ADR로 POC 제외), [0004-product-alpha](알파 정의 — pgvector 보조 언급 갱신), [0005-knowledge-graph-neo4j](2-store 유지, pgvector 보조 부분 갱신), [0001], [0003]. 반영: `doc/ref/architecture/`·`doc/ref/domains/`·`doc/ref/glossary/`·`doc/design/README.md`·`README.md`·`CLAUDE.md`.
