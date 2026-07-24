# CONVEY

**주식/시장 리서치를 유튜브 쇼츠로 바꾸는 자동 파이프라인** (한국어) — Python MSA (FastAPI · Kafka · Neo4j · PostgreSQL · Ollama · ffmpeg).

> **상태: 1차 개발 완료** — 로컬 도커 스택에서 *수집 → 그래프 → 스크립트 → 영상 합성 → 완성본 mp4*가 **무인 전자동**으로 돈다. 알파 4개 구현·e2e 검증. 외부 키·클라우드가 필요한 발행·인증·배포(C)는 의도적 이연. ← 정리 `doc/summary/20260724-summary-milestone-phase1.md`.
>
> **정본**은 `CLAUDE.md`(정체성·가드레일) · `doc/ref/`(아키텍처·도메인·용어) · `doc/decisions/`(ADR). 이 README는 개요·기동·컴포넌트 추가 가이드.
>
> 핵심 패턴(원형 `py-msa-ai` 계승): 게이트웨이 단일 진입 + **Supabase JWT(JWKS) 중앙검증**(ADR 0007) + HMAC 하류 신뢰헤더 · 트랜잭션 아웃박스 · URL prefix=도메인 경계 · 서비스별 DB · 공통 에러 스키마 · API 전용(BE).

## 목차
[알파](#알파--왜-이-시스템이-존재하나) · [파이프라인](#파이프라인-3단) · [구성](#구성) · [저장](#저장--하이브리드) · [빠른 시작](#빠른-시작) · [포트/토픽](#포트--토픽) · [컴포넌트 추가](#컴포넌트-추가) · [가드레일](#가드레일) · [문서 지도](#문서-지도) · [개발](#개발)

---

## 알파 — 왜 이 시스템이 존재하나

"스크립트 한 줄 → 영상"은 이미 외부 생성형 툴이 해주는 **커모디티**다. CONVEY는 그게 **못하는 4가지**에만 복잡도를 투자한다(전부 1차에서 구현):

1. **근거 있는 정확한 정보** ✅ — 주가·실적·이벤트를 환각 없이 출처와 함께. 관계마다 `source_article_id` 결속, 개방형 NER 본문 substring 환각컷. "안 틀리는 금융 콘텐츠".
2. **이슈 종목 자동 선별** ✅ — "오늘 뭘 만들지"를 시세 급변 + 뉴스 빈도로 자동 포착(`issue-detector`).
3. **정확한 차트·수치 렌더링** ✅ — 정확한 종가·등락률·차트를 영상에 결정론적으로 박기(matplotlib + ffmpeg 오버레이; 수치는 데이터에서만, LLM 생성 금지. 생성형 영상은 POC 제외 — ADR 0006).
4. **자동화·양산** ✅ — 이슈→제작 무인 루프, 일관 포맷으로 하루 N개 안정 양산.

커모디티(일반 대본 문장·broll·TTS·영상 스티칭·YouTube 업로드)는 외부 API로 얇게 외주. ← 정본 `doc/decisions/0004-product-alpha.md`.

## 파이프라인 (3단)

```
[A] 축적    KIS 시세 ─ market-feed ─┐   뉴스·RSS ─ news-feed(종목·사건 태깅) ─┐
                                    └──────────────────────────────────────┴─► research
                          개방형 NER(엔티티+관계, 로컬 Ollama) → Neo4j 지식 그래프 + Postgres(시세·기사)
                          ⇒ 축적에서 멈춤 (콘텐츠 자동 유발 X). 수집 멱등(source_url).

[B0] 선별   market.ticks + research.ingested ─► issue-detector ─► "오늘의 이슈 종목" 랭킹 → issue.selected
                          ⇒ 자동 양산(알파4) 또는 사람이 대시보드에서 선택

[B] 제작    이슈/기사 → content(잡)  ─ 운영 대시보드(무인증 로컬, :8091)에서 시나리오 승인 게이트
              ├─ agent: research/content /search(GraphRAG 관계 + 사실) → 근거 스크립트 → llm-inference(로컬 Ollama)
              ├─ (커모디티) edge-tts(한국어 TTS) · Pexels(broll) — video-assembly 내부에서 호출
              └─ video-assembly: 정확한 차트·수치 오버레이 + 자막 싱크 + 배경 컷 + ffmpeg → mp4
            완성본 → ✋사람 승인 → content.approved → publishing → YouTube Shorts [C1 이연]
```

> 상세: **`doc/ref/architecture/00.아키텍처.html`**(시각 정본 — 브라우저로 열기) · 텍스트 `01.research`·`02.content`·`03.publishing`·`04.issue-detector`.
> 그래프·Kafka를 처음 본다면 **`doc/ref/graph-kafka-guide.md`**(학습 가이드)부터.

## 구성

```
convey/
├─ docker-compose.yml       # Kafka(KRaft)·Postgres·Neo4j·게이트웨이·서비스. Ollama는 네이티브 재사용(기본) 또는 --profile ollama
├─ libs/common/             # [lib] 공통: 설정·에러스키마·JWT(JWKS)/HMAC·Kafka 유틸·종목 마스터(stocks)
├─ gateway/                 # 단일 진입(Supabase JWKS 검증 + HMAC 신뢰헤더 + 프록시). 라우트: /research·/content
├─ services/
│  ├─ market-feed/          # [워커] KIS 시세 → Kafka                         · 완료
│  ├─ news-feed/            # [워커] 뉴스·RSS 수집 + 종목·사건 태깅            · 완료
│  ├─ research/             # [API] Neo4j 지식그래프 + 개방형 NER + Postgres 사실 + /search(GraphRAG) · 완료
│  ├─ issue-detector/       # [워커] 이슈 종목 랭킹 → issue.selected(자동 양산) · 완료
│  ├─ content/              # [API] 제작 잡·스크립트·미디어 자산·승인 + 운영 대시보드(:8091) · 완료
│  ├─ agent/                # [API] 근거 스크립트(GraphRAG 2곳) → llm-inference · 완료
│  ├─ llm-inference/        # [API] 로컬 Ollama 추론 창구(llama3.2)             · 완료
│  ├─ video-assembly/       # [워커] 차트·수치 렌더 + TTS(edge-tts)·broll(Pexels) + ffmpeg 합성 · 완료
│  ├─ publishing/           # [API] YouTube 업로드·발행 승인                    · 스텁(C1 이연 — OAuth 키 대기)
│  └─ sample-domain/        # [참고] 원형 패턴 예시(아웃박스·이벤트 발행)
└─ infra/db/init/           # 서비스별 DB 생성 (벡터 확장은 POC 제외 — ADR 0006)
```

> **인증**: 자체 `auth` 서비스·`auth_db`는 제거하고 **Supabase**로 위임(ADR 0007). 게이트웨이는 JWKS 검증만. `llm-trainer`(원형 LoRA 트레이너)도 제거(톤은 moat가 아님 — ADR 0004).
> TTS·broll은 별도 서비스가 아니라 `video-assembly` 내부에서 edge-tts·Pexels로 호출(커모디티 얇게).

### 배포 형태 3종

| 형태 | 정체 | 게이트웨이 뒤 | 예 |
|:---|:---|:---:|:---|
| **① HTTP API** | 외부 요청 처리 | O | `research`·`content`·`agent`·`llm-inference`·`publishing` |
| **② 워커/데몬** | HTTP 없음, Kafka·외부연동 | ✗ | `market-feed`·`news-feed`·`issue-detector`·`video-assembly` |
| **③ 공유 lib** | import해서 씀 | — | `libs/common` |

> 예외: `content`의 **운영 대시보드**(:8091)는 게이트웨이를 우회하는 무인증·로컬 전용 화면(ADR 0010).

## 저장 — 하이브리드

LoRA(모델 튜닝)를 쓰지 않으므로 콘텐츠 품질의 유일한 레버는 **지식 레이어**다. 그래서 관계·인과를 그래프로 담는다(ADR 0005). **RAG는 벡터가 아니라 GraphRAG+SQL**(벡터/pgvector는 POC 제외 — ADR 0006).

| 저장소 | 소유 | 담는 것 | 역할 |
|:---|:---|:---|:---|
| **Neo4j** | `research` | 노드 `:Entity`(+아는 종목은 `:Stock`·ticker) · 엣지 5종(`HAS_EVENT`·`AFFECTS`·`SUPPLIES`·`COMPETES`·`BELONGS_TO`) | 관계·인과 **다홉 추론** = 알파① |
| **Postgres** (`research_db`) | `research` | 시세(PriceTick)·기사(Article+출처) | 사실 SQL 정확 조회 |
| **Postgres** (`content_db`) | `content` | 잡·스크립트·자산·완성본 상태 | 제작 상태. 히스토리 중복회피=키워드/메타 |
| **Supabase** (외부) | — | 계정·세션·JWT | 인증 위임(ADR 0007) |

> 진짜 일 = **추출 파이프라인**(뉴스 → 개방형 NER + 관계추출 → 그래프 엣지). 여기가 품질의 원천. **모든 엣지는 `source_article_id`에 결속**(무출처 관계 0 — 환각 방지).
> 벡터 의미검색(pgvector)은 POC 제외·보류. 필요해지면 Postgres 위에 분리 기능으로 재도입(ADR 0006).

## 빠른 시작

```bash
cp .env.example .env          # 시크릿 · KIS 키 · 미디어 API 키(Pexels) · YouTube OAuth · Neo4j 비번 · SUPABASE_*
scripts/up.sh                 # 전체 기동 (= docker compose up -d --build)
curl http://localhost:8080/health          # 게이트웨이(유일한 외부 진입점)

# 운영 대시보드(로컬 무인증) — 1차의 주 조작 화면
open http://localhost:8091                  # 오늘자 기사 → 시나리오 승인 → 배경 선택 → 쇼츠 생성·미리보기

# Ollama 모델 준비(런타임 1회 — 이미지 미포함). 기본은 호스트 네이티브 Ollama 재사용.
ollama pull llama3.2

# 인증: 로그인·발급은 Supabase(클라이언트가 supabase-js/REST). 게이트웨이는 검증만.
#   curl -H "Authorization: Bearer <supabase_access_token>" http://localhost:8080/research/search?q=...
```

> 호스트 포트는 `.env`의 `*_PORT`로 변경. `video-assembly` 컨테이너엔 ffmpeg 포함. 정지 `scripts/down.sh`, 데이터 초기화 `scripts/reset-data.sh`.
> 그래프·Kafka 접속·조회는 **`doc/ref/graph-kafka-guide.md`** 참조(Neo4j :7474 / kafka-ui :8090).

## 포트 / 토픽

| 대상 | 포트 | 노출 | | 토픽 | 발행 → 소비 |
|:---|:---|:---|---|:---|:---|
| gateway | 8080→8000 | 외부(유일 진입) | | `market.ticks` | market-feed → research·issue-detector |
| **대시보드**(content) | 8091→8000 | 로컬 무인증 | | `research.ingested` | news-feed → research·issue-detector (축적) |
| ollama | 11434 | 외부 | | `research.macro` | news-feed → research (거시지표) |
| neo4j | 7474·7687 | 개발 | | `issue.selected` | issue-detector → content (자동 양산) |
| postgres | 5432 | 개발 | | `content.generate` | content(on-demand) → content consumer |
| kafka-ui | 8090 | 관측 | | `media.assemble` | content → video-assembly |
| | | | | `content.assembled` | video-assembly → content (fan-in) |
| | | | | `content.ready` / `content.approved` | 완성(내부) / 사람 승인 → publishing |

> 이슈 랭킹·합성 진행상태는 이벤트가 아니라 내부 상태/조회. 발행은 사람 승인(`content.approved`) 후에만.

### 핵심 패턴 → 구현 위치

| 패턴 | 위치 |
|:---|:---|
| 게이트웨이 단일 진입 + Supabase JWKS 중앙검증 | `gateway/app/main.py`·`config.py` |
| HMAC 하류 신뢰헤더(우회 직접호출 차단) | `libs/common/common/security.py` |
| URL prefix = 도메인 경계 | `gateway/app/config.py` `routes` |
| 트랜잭션 커밋 후 이벤트 발행(간이 아웃박스) | `services/*/…/service.py` (참고: `sample-domain`) |
| API 서비스 + Kafka 소비 동거 | `services/content/app/consumer.py` |
| 개방형 NER + 그래프 upsert(근거 결속) | `services/research/app/extract/relations.py`·`graph/neo4j_repo.py` |
| 공통 에러 스키마 | `libs/common/common/errors.py` |
| 서비스별 DB 분리 | `infra/db/init/01-create-databases.sql` |

## 컴포넌트 추가

### ① HTTP API 서비스 (폴더 + compose + 게이트웨이 라우트 = 3종 세트)

1. **폴더**(기존 `services/research`·`content` 복사): `app/{__init__,main,config,db}.py` + `app/domains/<domain>/{router,service,repository,models,schemas}.py`.
2. **`docker-compose.yml`** 서비스 블록 추가 (build·`<<: *python-env`·`DATABASE_URL`·`depends_on`).
3. **`gateway/app/config.py`** `routes`에 `"/<name>": "http://<name>:8000"` 등록 (필수 — 안 하면 404).
4. **DB 필요 시** `infra/db/init/01-create-databases.sql`에 `CREATE DATABASE <name>_db;` (벡터 확장은 POC 제외 — ADR 0006).

### ② 워커/데몬 (외부 연동·백그라운드)

- `app/main.py`(FastAPI) 대신 **`app/worker.py`**(asyncio 루프), CMD `python -m app.worker`. 게이트웨이 라우트 등록 안 함.
- 외부 API는 **부패방지 계층**(래퍼 클라이언트)에 가둠. 결과는 **Kafka 발행**. 참고: `services/market-feed/`·`news-feed/`·`video-assembly/`.

### ③ 공유 라이브러리

`libs/<name>/` 생성 → 서비스 Dockerfile `pip install` + pyproject `dependencies` 추가.
> **경고**: 공유 lib는 결합을 만든다 — 횡단 관심사(인증·로깅·Kafka·공통 타입·종목 마스터)만. 도메인 로직 공유 금지(API·이벤트로).

## 가드레일

절대 금지(발췌 — 정본 `CLAUDE.md §4`):
- **텍스트 LLM은 로컬 Ollama만** — 외부 텍스트 LLM 금지(원문 보호). 미디어 생성만 외부 API 허용(부패방지 계층).
- **리서치 출처·라이선스 메타 보존 필수** — 무출처 콘텐츠 생성 금지. 스크립트의 모든 수치는 출처에 못박음.
- **콘텐츠 자동 발행 금지 — 사람 승인** — YouTube 업로드는 승인 후에만.
- **운영 DB 직접 접속 · `git push`/`merge` · 민감 파일 커밋 · 자동 커밋 금지.**

## 문서 지도

| 위치 | 내용 |
|:---|:---|
| `CLAUDE.md` | 정체성 · 워크플로우 · 가드레일 · 코딩 스타일 (정본) |
| `doc/ref/architecture/` | **`00.아키텍처.html`**(시각 정본) + 텍스트 `01~04` · README 인덱스 |
| `doc/ref/graph-kafka-guide.md` | 그래프DB·Kafka **학습 가이드**(처음 배우는 사람용) + 접속·조회 |
| `doc/ref/domains/` | 도메인 경계(research·content·publishing) |
| `doc/ref/glossary/01.terms.md` | 용어(종목·사건·지식 그래프·알파·커모디티…) |
| `doc/decisions/` | ADR `0001`~`0014` — `0004`(알파)·`0005`(Neo4j)·`0006`(POC 범위)·`0007`(Supabase)·`0010`(대시보드)·`0014`(개방형 NER) |
| `doc/design/backlog-deferred.md` | 이연(C) 목록 — YouTube 발행·클라우드 배포 |
| `doc/summary/20260724-…-milestone-phase1.md` | **1차 개발 완료 마일스톤** |

## 개발

```bash
make lint        # ruff
make typecheck   # mypy
make test        # pytest
make up / down / logs / build
```
