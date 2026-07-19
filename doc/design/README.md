# 설계 진행 가이드 (design roadmap)

> ✅ **아키텍처 설계 단계 완료 지점.** 이 개발 순서(빌드 ①~⑤)의 생성이 아키텍처/알파 설계 단계의 마지막 산출물이다.
> 완료된 것: 알파(ADR 0004) · 저장(Neo4j 그래프 ADR 0005) · 아키텍처(`00.아키텍처.html` + `doc/ref/architecture/`) · 도메인 경계 · 이 빌드 로드맵.
> **다음 단계 = 세부 도메인 설계**: 아래 라운드를 `/design` 커맨드로 하나씩(task-*.md + 계약) 진행.

> `/design`이 무엇을·어떤 순서로·어떤 계약으로 산출할지의 로드맵. 알파(`doc/decisions/0004`) 기반 빌드 순서를 따른다.
> 각 라운드 산출물 = `doc/design/{domain}/task-*.md`(자연어 설계) + 계약 파일(`api-contract.py`, `workflow.config.json`의 contract gate로 검증).

## 원칙

- **알파에 복잡도, 커모디티는 얇게**: 근거 데이터·이슈 선별·정확 렌더·양산에 설계를 투자. broll·TTS·유튜브 업로드는 외부 API 래퍼로 최소 설계.
- **빌드 순서 = 의존성 순**: 아래를 쌓아야 위가 성립. 한 라운드 끝나면 `/builder` → `/sync`.
- **계약 우선**: 엔티티·엔드포인트·이벤트 페이로드는 계약 파일이 정본. task-*.md엔 자연어 설계만(중복 금지).

## 라운드 로드맵

### 라운드 ① — 데이터 기반 (알파1) ★먼저
- **대상**: `research`(**Neo4j 지식 그래프** + Postgres 사실), `news-feed`(수집+태깅+추출), `market-feed`(시세 실사용)
- **산출**: `doc/design/research/task-*.md` + 계약
- **정해야 할 것**:
  - **그래프 모델**: 노드(Stock·Event·Sector·Company) · 엣지(AFFECTS·SUPPLIES·COMPETES·HAS_EVENT·BELONGS_TO)
  - **추출 파이프라인**(품질 원천): 뉴스 → NER(개체명 인식) + 관계추출 → 엣지. 어디까지 자동/규칙/LLM인지
  - Postgres 스키마(PriceTick·Article), 그래프↔사실 ID 연결. **벡터 임베딩 없음**(ADR 0006)
  - `GET /research/search` 계약(그래프 traversal + SQL 사실 회수 = GraphRAG), `market.ticks`·`research.ingested` 페이로드
- **코드 델타**: `research-feed/`→`news-feed/` 개명·`llm-trainer` 제거·벡터 흔적 정리 **완료**. 남은 것: research에 **Neo4j 드라이버** + Postgres 병행, `docker-compose`에 **Neo4j 컨테이너** 추가, research 모델 재작성(현재 TODO 자리표시).

### 라운드 ② — 이슈 선별 (알파2)
- **대상**: `issue-detector`(신규 워커)
- **정해야 할 것**: 랭킹 지표(시세 변동성·거래량·뉴스 빈도)+윈도우, Kafka 스트림 집계 방식(DB 경계 유지), 출력(조회 API vs `issue.detected`).
- **코드 델타**: `services/issue-detector/` 신규(market-feed 골격 참고), compose·gateway 연동.

### 라운드 ③ — 근거 스크립트 (알파1)
- **대상**: `agent`(근거회수 연결·엄격 인용), `content`(생성 잡·스크립트 저장)
- **정해야 할 것**: agent `retriever`를 `research/content /search` **HTTP 호출**로 연결(저장소 직접접근 X, **벡터 아님 — GraphRAG+SQL**), 프롬프트에 **출처·수치 인용 강제**, `content.generate` 잡 계약, Script 엔티티(인용 근거 포함).
- **코드 델타**: agent config에 `research_url`·`content_url`·`retrieval_top_k` **추가 완료**, retriever HTTP 근거회수 스텁 **작성 완료** → round③에서 실제 호출 구현. (임베딩·`/embeddings`는 벡터 제외로 불필요 — ADR 0006)

### 라운드 ④ — 정확 렌더 (알파3)
- **대상**: `video-assembly`(차트·수치 오버레이+ffmpeg), `image-gen`·`tts`(외주 얇게)
- **정해야 할 것**: 쇼츠 **템플릿**(차트·종가·등락률·자막 레이아웃), research 데이터→렌더 데이터 매핑, fan-out/join, **미디어 바이너리 저장소**(MinIO/S3 vs 볼륨 — 미결).
- **POC 경계(ADR 0006)**: 화면 위 정확 수치·차트는 우리가 결정론적 렌더. **생성형 영상 모델은 POC 제외** — 배경(스톡/모션)+차트 애니+텍스트 오버레이+TTS로 시작.
- **코드 델타**: 미디어 서비스 신규, ffmpeg Dockerfile, 저장소 컴포넌트.

### 라운드 ⑤ — 양산 루프 (알파4)
- **대상**: 스케줄 트리거, 잡 재개(신뢰성), `publishing`(YouTube)
- **정해야 할 것**: 잡 상태머신 기반 **재개/재시도**(간이 아웃박스 유실 보완), 스케줄러, 발행 승인 워크플로우, `content.approved`→YouTube 업로드.
- **코드 델타**: content 잡 재개 로직, `services/publishing/` 신규, 스케줄 워커.

## 아키텍처 정합 확인 (설계 착수 전 필수 참조)
- `doc/ref/architecture/00.아키텍처.html`(시각 정본) · `01~04`(도메인별 텍스트)
- `doc/ref/domains/`(경계) · `doc/decisions/0004`(알파) · `0005`(그래프 저장소) · `0006`(POC 범위·벡터제외·영상경계)
- `doc/ref/glossary/terms.md`(용어)

## 현재 스캐폴드 vs 목표 (라운드 ① 정합 진행)

정합 정리 1차 완료(ADR 0006). 진행 상태:

- ✅ `services/research-feed/` → **`news-feed/` 개명 완료** (+ 종목·사건 태깅 역할 반영)
- ✅ `services/llm-trainer/` → **제거 완료** (llm-inference `/train` 엔드포인트도 제거)
- ✅ 벡터/pgvector 흔적 제거 완료(코드·compose·infra·pyproject) — RAG는 GraphRAG+SQL (ADR 0006)
- `services/market-feed/` → 삭제 대상 아님, **실사용으로 복귀**(예정)
- `services/issue-detector/` → **신규**(아직 없음 — 라운드②)
- `services/research/` → Neo4j 지식 그래프 + Postgres 사실 하이브리드로 확정(현재 TODO 자리표시). **compose에 Neo4j 추가는 라운드① 남은 작업.**
- 미디어: `image-gen`·`tts`는 외주 얇게, `video-clip`·생성형 영상은 보류(POC 제외), `video-assembly`만 자체

## 커모디티 처리 원칙
broll·TTS·영상 스티칭·YouTube 업로드는 알파가 아니므로 **외부 API 부패방지 계층으로 최소 구현**. 아무 라운드에나 얇게 삽입 가능(설계 깊이 최소).
