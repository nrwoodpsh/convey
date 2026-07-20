# CONVEY 온보딩

> **주식/시장 리서치를 유튜브 쇼츠로 바꾸는 자동 파이프라인** (한국어). Python MSA. API 전용(BE).
> 이 문서 하나로 "무엇을·어디까지·어떻게 이어서" 파악한다. 정본은 `CLAUDE.md` + `doc/ref/` + `doc/decisions/`.

## 30초 요약 — 왜 존재하나

"스크립트 → 영상"은 외부 생성툴이 하는 **커모디티**. CONVEY는 그게 **못하는 4가지(알파)**에만 복잡도를 투자한다:

1. **근거 있는 정확한 정보** — 주가·실적을 환각 없이 출처와 함께
2. **이슈 종목 자동 선별** — 시세급변+뉴스빈도로 "오늘 뭘 만들지"
3. **정확한 차트·수치 렌더링** — 생성형이 못 박는 정확한 숫자를 화면에
4. **자동화·양산** — 일관 포맷 안정 양산

커모디티(broll·TTS·스티칭·업로드)는 외부 API로 얇게. ← `doc/decisions/0004`.

## 파이프라인 (3단)

```
[축적] KIS시세─market-feed┐  뉴스─news-feed(종목·사건 태깅)┐
                          └────────────────────────────────┴─► research
                          추출(규칙 태깅+LLM 관계추출) → Neo4j 그래프 + Postgres 사실
[선별] market.ticks + research.ingested ─► issue-detector ─► 이슈 종목 랭킹 ─► ✋사람 선택
[제작] POST /content/generate ─► content(잡) ─ agent(근거 스크립트) ─ 미디어(외주) ─ video-assembly(정확 렌더+ffmpeg) ─► mp4
       ─► ✋사람 승인 ─► publishing ─► YouTube Shorts
```

- **도메인 3개**: `research`(축적·알파1의 심장) · `content`(제작) · `publishing`(발행). 나머지는 컴포넌트.
- **RAG = GraphRAG+SQL**(벡터/pgvector POC 제외 — ADR 0006). 텍스트 추론은 **로컬 Ollama만**.
- 인증은 **Supabase**(ADR 0007). 게이트웨이가 JWKS 검증 + 하류 HMAC 신뢰헤더.

## 지금 어디까지 됐나 (2026-07-20 기준)

**전 라운드 코어 구현 + 실서비스 자체검증 완료.** 알파 4개 중 3개 실증(④는 멱등 발행까지).

| 라운드 | 구현 | 검증 |
|:---|:---|:---|
| R0 인증(Supabase JWKS) | 게이트웨이 검증, auth 서비스 제거 | 단위(자체키 시뮬) |
| R① research | 규칙 태깅·LLM 추출·Neo4j 그래프·`/search`(GraphRAG)·consumer | **실 Ollama·Neo4j·PG + Kafka 전송 e2e** |
| R② issue-detector | 가중합 랭킹 워커 + `/issues/today` | 결정론 단위 |
| R③ content·agent | 근거 스크립트(수치=데이터)·잡 상태머신 | 실 Ollama·PG |
| R④ video-assembly | 정확 차트·수치 렌더 + ffmpeg 합성 | 실 matplotlib·ffmpeg(PNG→mp4) |
| R⑤ publishing | 멱등 발행 상태머신·부패방지 스텁 | 실 PG |

> 검증 원칙: 알파 로직은 결정론 단위테스트, 외부 의존은 실서비스 라이브. "미검증"은 문서에 정직히 표시(각 `doc/design/*/task-*.md` History).

**아직 안 된 것(=다음 작업)**: 외부 실연동 — KIS 시세·RSS 실수집, image-gen·tts, YouTube OAuth, Supabase 프로젝트. content/issue-detector/publishing consumer 전송 e2e(research와 동일 패턴). 폴리시: publishing POST 엔드포인트·한글폰트(fonts-nanum)·타입 노드(Stock/Sector)·스케줄 워커.

## 로컬 개발 환경 (도커-올)

인프라는 **전부 도커 + 네이티브 Ollama**. 접속 포트(로컬):

| 서비스 | 접속 | 비고 |
|:---|:---|:---|
| Postgres | `localhost:5432` (app/app) | 도커 컨테이너. DB: research_db·content_db·publishing_db·sample_db |
| Neo4j | `bolt://localhost:7687` (neo4j/convey-dev-pw)·http 7474 | 도커. Community=인스턴스당 DB 1개 |
| Kafka | 내부 `kafka:9092` · **호스트 `localhost:29092`** | 도커. 호스트 검증은 29092 |
| Ollama | `localhost:11434` | **네이티브**(모델 `qwen3:14b`) |

> 사용자 네이티브 PG(Homebrew postgresql@14)는 **중지됨**(도커 postgres가 5432 점유). 되돌리기 `brew services start postgresql@14`. 타 프로젝트 백업 `~/pg-backups-20260720/`.

**기동:**
```bash
cp .env.example .env          # SUPABASE·KIS·미디어·YouTube 키는 실연동 시 채움
docker compose up -d postgres neo4j kafka   # 인프라(필요 서비스만)
docker compose up -d --build  # 전체(앱 포함)
```

**검증 재현(로컬, 서비스 미기동 상태에서 모듈 직접):**
```bash
# 예: research 단위테스트 / 실 스택 스크립트는 PYTHONPATH로 common+서비스 경로 주입
PYTHONPATH=services/research:libs/common python -m pytest services/research/tests/ -q
python -m mypy --strict --ignore-missing-imports <파일>   # 계약·구현 타입체크
```
> dev 도구는 로컬 설치됨: mypy·pytest·pyjwt·cryptography·asyncpg·greenlet·neo4j·aiokafka·matplotlib.

## 문서 지도

| 위치 | 내용 |
|:---|:---|
| `CLAUDE.md` | 정체성·워크플로우·가드레일·코딩스타일 (정본) |
| `doc/ref/README.md` | 입력 정본 마스터 인덱스(architecture·domains·glossary·patterns) |
| `doc/ref/architecture/00.아키텍처.html` | 시각 정본(브라우저) + `01~04` md |
| `doc/decisions/` | ADR 0001~0007 (0004 알파·0005 그래프·0006 POC범위·0007 인증) |
| `doc/design/{domain}/` | 라운드별 `task-*.md`(자연어 설계) + `api-contract.py`(계약) |
| `doc/summary/` | 라운드별 구현 요약 |

## 워크플로우 (flow 플러그인)

`design → builder → sync → commit`. 오케스트레이션은 `/run`(design 컨펌·commit·push는 사람 게이트). 커밋은 `/commit`으로만, **push·merge는 사람이 외부 툴로**.

## 가드레일 (절대)

- **텍스트 LLM은 로컬 Ollama만** — 외부 텍스트 LLM 금지(원문 보호). 미디어 생성만 외부 API(부패방지 계층).
- **출처·라이선스 메타 필수** — 무출처 콘텐츠 생성 금지. 스크립트 수치는 사실 데이터에서만(환각 차단).
- **발행은 사람 승인 후에만** — `content.approved` 게이트.
- **push·merge·자동커밋 금지** — 커밋만 `/commit`, push는 사람.
- **운영 DB 직접접속·민감파일 커밋 금지**.

## 다음 세션 시작 체크리스트

1. `docker ps`로 postgres·neo4j·kafka 떠 있는지(없으면 `docker compose up -d postgres neo4j kafka`), `ollama list`로 qwen3:14b 확인.
2. `git log --oneline`로 진척 확인, `doc/summary/`로 라운드별 상태 파악.
3. 외부 연동 착수: `/run`으로 라운드 이어가거나(consumer e2e), 외부 키 준비 후 실수집(KIS/RSS)부터.
