# CLAUDE.md

## 1. 프로젝트 정체성

- **프로젝트명**: CONVEY
- **한 줄 정의**: **주식/시장 리서치를 유튜브 쇼츠(영상+이미지)로 바꾸는** 자동 파이프라인 (research → shorts). 한국어.
- **기술 스택**: Python 3.11 MSA — FastAPI · Kafka(KRaft) · PostgreSQL(서비스별 DB — 시세·기사 사실) · **Neo4j(지식 그래프 — 종목·사건 관계·인과)** · Ollama(로컬 LLM) · KIS OpenAPI(시세) · 외부 미디어 API(broll·TTS — 커모디티) · ffmpeg(차트·수치 렌더+합성) · SQLAlchemy · Alembic · **Supabase Auth**(인증 — 원형 자체 JWT 대체, ADR 0007). API 전용(BE). ※ RAG는 **GraphRAG+SQL**, 벡터(pgvector)는 POC 제외(ADR 0006).
- **원형**: `py-msa-ai` (`nrwoodpsh/py-msa-ai-starter`) — 게이트웨이 단일 진입 + JWT 중앙검증 + HMAC 신뢰헤더 + 트랜잭션 아웃박스.
- **주요 도메인(확정 — 3도메인)**: `research`(시세·뉴스를 **종목·사건 관계 그래프(Neo4j)+사실(Postgres)**로 저장) · `content`(스크립트·미디어 자산·완성본) · `publishing`(발행). 스크립트 생성은 `agent`, 이슈 선별은 `issue-detector`(컴포넌트), 정확 렌더+합성은 `video-assembly`, broll·TTS는 외주. 미디어 산출물 상태는 `content` 소유. ← `doc/ref/domains/`·`doc/ref/architecture/`.
- **파이프라인 성격**: 원형(텍스트 LLM)에서 **멀티미디어(쇼츠) 파이프라인**으로 확장, **3단(축적→선별→제작)**. 발행 채널 **YouTube Shorts**. ← 전환 배경 `doc/decisions/`.
- **알파(차별점) — 투자 우선순위의 최상위 근거**: ①근거 있는 정확한 정보(출처·환각금지) ②이슈 종목 자동 선별 ③정확한 차트·수치 렌더링 ④자동화·양산. 커모디티(일반 스크립트 문장·broll·TTS·스티칭)는 외부 API로 얇게. ← 정본 `doc/decisions/0004-product-alpha.md`.

---

## 2. 워크플로우

본 프로젝트는 `flow` 플러그인을 사용한다. 진입점은 상황별로 고른다:

| 상황 | 흐름 |
|:---|:---|
| 신규 기능 | `/design` → `/builder` → `/sync` |
| 버그·장애 | `/troubleshoot` → `/builder`(또는 직접 수정) → `/sync` |
| 레거시 파악 | `/analysis` → `/design` → … |
| 품질 점검 | `/review` (필요할 때 오버레이) |
| 커밋 | `/commit` (요청 시에만 — 목록·메시지 작성 후 커밋. push·merge는 사람) |

> **핵심 규칙: 여러 문 입장, 한 문 퇴장.** 어떤 진입점이든 코드 변경은 반드시 `/sync`로 수렴한다(드리프트 방지). 커밋은 `/commit`이 준비 시 `drift-check`로 문서 동기화를 확인한다.

검증 명령·계약 형식은 `workflow.config.json`에 정의한다.

---

## 3. 참조 통제

### 항상 참조 (인덱스 상시, 본문은 선택 로드)
- `doc/ref/domains/` — 도메인 경계·맵 (신규 설계 전 필수 확인)
- `doc/ref/architecture/` — 아키텍처·기술 스택·크로스커팅 제약(UTC·금액단위 등)
- `doc/ref/patterns/` — 확정 패턴(layout·api·error·task) ← AI가 참조하는 정본
- `doc/ref/db-schema/` — DB DDL (index=테이블 목록, 본문 선택 로드)
- `doc/ref/glossary/` — 용어집

### 참조 금지 (자동 로드 안 함, 필요 시 `@`로 명시 주입)
- `doc/analysis/` — 일회성 분석·트러블슈팅
- `doc/design/{작업 중 아닌 타 도메인}/`

> `doc/summary/`·`doc/decisions/`는 참조 허용. Claude Code는 자동 RAG가 없으므로 참조는 항상 명시적(Read/Grep/Glob/`@` 또는 `explorer` 위임). "상시"는 로드가 아니라 인덱스만 — 큰 본문은 선택 로드.

---

## 4. 가드레일 (절대 금지)

- **운영 DB 직접 접속 금지** — `doc/ref/db-schema/`의 DDL만 참조. 실행은 사람이.
- **`git push`·`merge`·`reset --hard`·`clean -f`·force-push 금지** — Claude는 실행하지 않는다. push·merge는 사람이 외부 툴로.
- **민감 파일 커밋 금지** — `.env`, `*.key`, `*-prod.*` 등. (원형은 `.env.example`만 제공, `.env`는 사람이 생성)
- **자동 커밋 금지** — 커밋은 사용자가 요청할 때 `/commit`으로만. `/sync` 등 다른 커맨드는 커밋하지 않는다.
- **텍스트 LLM은 로컬 Ollama만 — 외부 텍스트 LLM API 금지** — 리서치 원문·스크립트 등 텍스트 추론은 외부 LLM 서비스로 나가지 않도록 `llm-inference` → `ollama`(로컬)로만. 원문 데이터 보호가 목적. (RAG는 GraphRAG+SQL이라 임베딩 없음; 후속 라운드에서 임베딩 도입 시에도 로컬 Ollama만.)
- **미디어 생성은 외부 API 허용 (부패방지 계층 경유)** — 이미지·TTS·영상클립 생성은 외부 API를 쓸 수 있다. 단 호출은 반드시 래퍼 서비스(`image-gen`·`tts`·`video-clip`)의 부패방지 계층에 가두고, **원문 텍스트 전체를 외부로 넘기지 않는다**(생성에 필요한 프롬프트·에셋만). 영상합성은 로컬 ffmpeg(`video-assembly`).
- **리서치 출처·저작권 메타 보존 필수** — 수집 원문은 출처 URL·라이선스 메타를 반드시 함께 저장. 무출처 콘텐츠 생성 금지. 미디어 자산도 생성 소스·라이선스 메타를 계승·기록.
- **콘텐츠 자동 발행 금지 — 사람 승인** — 파이프라인은 완성본(쇼츠 mp4·이미지) 생성까지 전자동. 최종 발행(**YouTube Shorts** 업로드 등 외부)은 사람 승인 후에만.

---

## 5. 코딩 스타일 (프로젝트 고유만)

- **언어/런타임**: Python 3.11, 전면 타입힌트(`from __future__ import annotations`), async 우선(FastAPI·asyncio).
- **네이밍**: 모듈·함수·변수 `snake_case`, 클래스 `PascalCase`, 상수 `UPPER_SNAKE`. 서비스/컨테이너명 `kebab-case`(예: `llm-inference`).
- **폴더 구조**: `services/<service>/app/domains/<domain>/{router,service,repository,models,schemas}.py` (레이어링 router→service→repository→models). 도메인 1개뿐인 작은 서비스는 flat 허용.
- **린트/포맷/타입**: `ruff`(line-length 100, rules E·F·I·UP·B·ASYNC) + `mypy --strict`. FastAPI DI(`Depends()` 등) 기본값은 B008 예외 처리됨.
- **DB 마이그레이션**: Alembic (`services/<service>/alembic/versions/`).
- **테스트**: `pytest`(asyncio_mode=auto), `testpaths = services·libs·gateway`.
- **커밋 메시지**: Conventional Commits — `<type>(<scope>): 요약`. type: `feat`·`fix`·`docs`·`refactor`·`test`·`chore` 등, scope는 도메인/서비스(예: `content`·`research`·`gateway`). 예: `feat(content): 초안 생성 API 추가`.

---

## 6. 도구 정책 (프로젝트 고유만)

- **MCP**: **DB MCP(읽기 전용 스키마 조회)만 허용.** 그 외 MCP는 미승인.
  - Notion MCP는 아직 미승인 → `/publish`(Notion 발행)는 현재 불가. 필요 시 별도 승인 후 활성화.
- **외부 API 자격증명**: 미디어 생성 API 키·YouTube OAuth 토큰은 `.env`로만 주입(커밋 금지, `.env.example`에 키 이름만). YouTube 업로드는 발행 승인 워크플로우를 통과한 뒤에만 실행.
- **LSP(제안)**: `pyright`/`pylsp` (Python). 설치·바이너리는 사람이.
