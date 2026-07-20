# CONVEY

**주식/시장 리서치를 유튜브 쇼츠로 바꾸는 자동 파이프라인** (한국어) — Python MSA (FastAPI · Kafka · Neo4j · PostgreSQL · Ollama · ffmpeg).

> 원형: `py-msa-ai` (`nrwoodpsh/py-msa-ai-starter`)에서 복제. **정본**은 `CLAUDE.md`(정체성·가드레일) · `doc/ref/`(아키텍처·도메인·용어) · `doc/decisions/`(ADR). 이 README는 개요·기동·컴포넌트 추가 가이드.
>
> 핵심 패턴(원형 계승): 게이트웨이 단일 진입 + JWT 중앙검증 + HMAC 하류 신뢰헤더 · 트랜잭션 아웃박스 · URL prefix=도메인 경계 · 서비스별 DB · 공통 에러 스키마 · API 전용(BE).

## 목차
[알파](#알파--왜-이-시스템이-존재하나) · [파이프라인](#파이프라인-3단) · [구성](#구성) · [저장](#저장--하이브리드) · [빠른 시작](#빠른-시작) · [포트/토픽](#포트--토픽) · [컴포넌트 추가](#컴포넌트-추가) · [가드레일](#가드레일) · [문서 지도](#문서-지도) · [개발](#개발)

---

## 알파 — 왜 이 시스템이 존재하나

"스크립트 한 줄 → 영상"은 이미 외부 생성형 툴이 해주는 **커모디티**다. CONVEY는 그게 **못하는 4가지**에만 복잡도를 투자한다:

1. **근거 있는 정확한 정보** — 주가·실적·이벤트를 환각 없이 출처와 함께. "안 틀리는 금융 콘텐츠".
2. **이슈 종목 자동 선별** — "오늘 뭘 만들지"를 시세 급변 + 뉴스 빈도로 자동 포착.
3. **정확한 차트·수치 렌더링** — 생성형 영상툴이 못하는 정확한 종가·등락률·차트를 영상에 박기(화면 위 픽셀은 우리가 결정론적 렌더·합성; 생성형 영상은 POC 제외 — ADR 0006).
4. **자동화·양산** — 일관 포맷으로 하루 N개 안정 양산.

커모디티(일반 대본 문장·broll·TTS·영상 스티칭·YouTube 업로드)는 외부 API로 얇게 외주. ← 정본 `doc/decisions/0004-product-alpha.md`.

## 파이프라인 (3단)

```
[A] 축적    KIS 시세 ─ market-feed ─┐   뉴스·RSS ─ news-feed(종목·사건 태깅) ─┐
                                    └──────────────────────────────────────┴─► research
                          추출(NER+관계) → Neo4j 지식 그래프(관계·인과) + Postgres(시세·기사)
                          ⇒ 축적에서 멈춤 (콘텐츠 자동 유발 X)

[B0] 선별   market.ticks + research.ingested ─► issue-detector ─► "오늘의 이슈 종목" 랭킹
                          ⇒ 사람이 확인·선택

[B] 제작    이슈 종목 → POST /content/generate ─► content(잡)
              ├─ agent: research/content /search(RAG 그래프+사실) → 근거 스크립트 → llm-inference(로컬)
              ├─ (외주) image-gen·tts → 외부 미디어 API
              └─ video-assembly: 정확한 차트·수치 오버레이 + ffmpeg → mp4
            완성본 → ✋승인 → content.approved → publishing → YouTube Shorts
```

> 상세: **`doc/ref/architecture/00.아키텍처.html`**(시각 정본 — 브라우저로 열기) · 텍스트 `01.research`·`02.content`·`03.publishing`·`04.issue-detector`.

## 구성

```
convey/
├─ docker-compose.yml       # Kafka(KRaft)·Postgres·Ollama·게이트웨이·서비스 (Neo4j는 round①)
├─ libs/common/             # [lib] 공통: 설정·에러스키마·JWT/HMAC·Kafka 유틸
├─ gateway/                 # 단일 진입(JWT 검증 + HMAC 신뢰헤더 + 프록시)
├─ services/
│  ├─ auth/                 # [API] JWT 발급(로그인)
│  ├─ market-feed/          # [워커] KIS 시세 → Kafka                      · 원형 실사용
│  ├─ news-feed/            # [워커] 뉴스·RSS 수집 + 종목·사건 태깅         · research-feed 개명 완료
│  ├─ research/             # [API] Neo4j 지식그래프 + Postgres 사실 + /search(GraphRAG) · 골격O
│  ├─ issue-detector/       # [워커] 이슈 종목 랭킹                         · 신규(예정)
│  ├─ content/              # [API] 제작 잡·스크립트·미디어 자산·승인        · 골격O
│  ├─ agent/                # [API] 근거 스크립트(RAG 2곳) → llm-inference   · 확장
│  ├─ llm-inference/        # [API] 로컬 Ollama 추론 창구
│  ├─ image-gen/ · tts/     # [워커] broll·TTS 외부 API 래퍼(커모디티)       · 신규(예정)
│  ├─ video-assembly/       # [워커] 차트·수치 렌더 + ffmpeg 합성            · 신규(예정)
│  └─ publishing/           # [API] YouTube 업로드·발행 승인                 · 신규(예정)
└─ infra/db/init/           # 서비스별 DB 생성 (벡터 확장은 POC 제외 — ADR 0006)
```

> **구현 순서**는 `doc/design/README.md`의 빌드 ①~⑤(데이터 기반 → 선별 → 스크립트 → 렌더 → 양산). 현재는 `research`·`content` 골격과 인프라 연동까지. `llm-trainer`(원형 LoRA 트레이너)는 **제거 완료**(톤은 moat가 아님 — ADR 0004).

### 배포 형태 3종

| 형태 | 정체 | 게이트웨이 뒤 | 예 |
|:---|:---|:---:|:---|
| **① HTTP API** | 외부 요청 처리 | O | `auth`·`research`·`content`·`agent`·`llm-inference`·`publishing` |
| **② 워커/데몬** | HTTP 없음, Kafka·외부연동 | ✗ | `market-feed`·`news-feed`·`issue-detector`·`video-assembly` |
| **③ 공유 lib** | import해서 씀 | — | `libs/common` |

## 저장 — 하이브리드

LoRA(모델 튜닝)를 쓰지 않으므로 콘텐츠 품질의 유일한 레버는 **지식 레이어**다. 그래서 관계·인과를 그래프로 담는다(ADR 0005). **RAG는 벡터가 아니라 GraphRAG+SQL**(벡터/pgvector는 POC 제외 — ADR 0006).

| 저장소 | 소유 | 담는 것 | 역할 |
|:---|:---|:---|:---|
| **Neo4j** (`research_graph`) | `research` | 노드(Stock·Event·Sector) + 엣지(AFFECTS·SUPPLIES·COMPETES) | 관계·인과 **다홉 추론** = 알파① |
| **Postgres** (`research_db`) | `research` | 시세(PriceTick)·기사(Article+출처) | 사실 SQL 정확 조회 |
| **Postgres** (`content_db`) | `content` | 잡·스크립트·자산·완성본 상태 | 제작 상태. 히스토리 중복회피=키워드/메타 |
| **Postgres** (`auth_db`) | `auth` | 계정 | 인증 |

> 진짜 일 = **추출 파이프라인**(뉴스 → NER + 관계추출 → 그래프 엣지). 여기가 품질의 원천.
> 벡터 의미검색(pgvector)은 POC 제외·보류. 필요해지면 Postgres 위에 분리 기능으로 재도입(ADR 0006).

## 빠른 시작

```bash
cp .env.example .env          # 시크릿 · KIS 키 · 미디어 API 키 · YouTube OAuth · Neo4j 비번
docker compose up -d --build  # 전체 기동
curl http://localhost:8080/health

# Ollama 모델 준비(런타임 1회 — 이미지 미포함)
docker compose exec ollama ollama pull llama3.2          # 스크립트 생성(한국어 모델 검토)

# 로그인 → 토큰
curl -s -X POST http://localhost:8080/auth/login \
  -H 'content-type: application/json' -d '{"username":"demo","password":"demo"}'
```

> 호스트 포트는 `.env`의 `*_PORT`로 변경. `video-assembly` 컨테이너엔 ffmpeg 포함.

## 포트 / 토픽

| 대상 | 포트 | 노출 | | 토픽(/design 확정) | 발행 → 소비 |
|:---|:---|:---|---|:---|:---|
| gateway | 8080→8000 | 외부 | | `market.ticks` | market-feed → research·issue-detector |
| ollama | 11434 | 외부 | | `research.ingested` | news-feed → research·issue-detector (축적) |
| neo4j | 7474·7687 | 개발 | | `content.generate` | content(on-demand) → content consumer |
| postgres | 5432 | 개발 | | `image.generate`·`tts.generate` | content → 미디어(외주) |
| kafka-ui | 8090 | 관측 | | `content.approved` | 사람 승인 → publishing |
| | | | | `content.published` | publishing → (관측) |

> 이슈 종목 랭킹·합성 완료는 이벤트가 아니라 내부 상태/조회. 발행은 사람 승인(`content.approved`) 후에만.

### 핵심 패턴 → 구현 위치

| 패턴 | 위치 |
|:---|:---|
| 게이트웨이 단일 진입 + JWT 중앙검증 | `gateway/app/main.py` |
| HMAC 하류 신뢰헤더(우회 직접호출 차단) | `libs/common/common/security.py`·`gateway_auth.py` |
| URL prefix = 도메인 경계 | `gateway/app/config.py` `routes` |
| 트랜잭션 커밋 후 이벤트 발행(간이 아웃박스) | `services/*/…/service.py` (참고: `sample-domain`) |
| API 서비스 + Kafka 소비 동거 | `services/content/app/consumer.py` |
| 공통 에러 스키마 | `libs/common/common/errors.py` |
| 서비스별 DB 분리 | `infra/db/init/01-create-databases.sql` |

## 컴포넌트 추가

### ① HTTP API 서비스 (폴더 + compose + 게이트웨이 라우트 = 3종 세트)

1. **폴더**(기존 `services/research`·`content` 복사): `app/{__init__,main,config,db}.py` + `app/domains/<domain>/{router,service,repository,models,schemas}.py`.
2. **`docker-compose.yml`** 서비스 블록 추가 (build·`<<: *python-env`·`DATABASE_URL`·`depends_on`).
3. **`gateway/app/config.py`** routes에 `"/<name>": "http://<name>:8000"` 등록 (필수 — 안 하면 404).
4. **DB 필요 시** `infra/db/init/01-create-databases.sql`에 `CREATE DATABASE <name>_db;` (벡터 확장은 POC 제외 — ADR 0006).

### ② 워커/데몬 (외부 연동·백그라운드)

- `app/main.py`(FastAPI) 대신 **`app/worker.py`**(asyncio 루프), CMD `python -m app.worker`. 게이트웨이 라우트 등록 안 함.
- 외부 API는 **부패방지 계층** `app/external_client.py`에 가둠. 결과는 **Kafka 발행**. 참고: `services/market-feed/`·`news-feed/`.

### ③ 공유 라이브러리

`libs/<name>/` 생성 → 서비스 Dockerfile `pip install` + pyproject `dependencies` 추가.
> **경고**: 공유 lib는 결합을 만든다 — 횡단 관심사(인증·로깅·Kafka·공통 타입)만. 도메인 로직 공유 금지(API·이벤트로).

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
| `doc/ref/domains/` | 도메인 경계(research·content·publishing) |
| `doc/ref/glossary/01.terms.md` | 용어(종목·사건·지식 그래프·알파·커모디티…) |
| `doc/decisions/` | ADR — `0004`(알파)·`0005`(Neo4j 그래프)·`0001~0003` |
| `doc/design/README.md` | 설계 진행 가이드(빌드 ①~⑤ 로드맵) |

## 개발

```bash
make lint        # ruff
make typecheck   # mypy
make test        # pytest
make up / down / logs / build
```
