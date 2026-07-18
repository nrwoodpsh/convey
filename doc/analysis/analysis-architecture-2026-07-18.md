# 분석 — CONVEY 아키텍처 설계 준비 (2026-07-18)

> ⚠️ **과거 스냅샷.** 이후 알파(정확·선별·렌더·양산)·Neo4j 지식 그래프 결정으로 방향이 갱신됨.
> 정본은 `doc/decisions/0004`·`0005`, `doc/ref/architecture/00~04`, `doc/design/README.md`. 아래는 당시 기록.

## 분석 대상 범위 (무엇을 읽었나)
- 원형 코드: `services/{agent,auth,llm-inference,llm-trainer,market-feed,sample-domain}`, `gateway/`, `libs/common/`, `docker-compose.yml`, `infra/db/init/`
- 문서층: `CLAUDE.md`, `doc/ref/architecture/README.md`, `doc/ref/domains/{research,content,publishing}.md`

## 핵심 발견 — 원형이 "주는 것" vs 설계가 "정해야 할 것"

### 이미 있는 것 (원형 계승, 재설계 불필요)
- **단일 진입 + 인증**: gateway(JWT) + HMAC 신뢰헤더 + 서비스별 DB + 간이 아웃박스 이벤트 — 골격 완성.
- **LLM 3레이어**: `agent`(오케스트레이션) → `llm-inference`(서빙 창구) → `ollama`(모델 실물). 로컬 전용 = 가드레일 "외부 LLM 금지"와 정합.
- **agent 내부 골격**: `agent/loop.py`(RAG검색→프롬프트조립→LLM호출→도구→응답), `tools/`, `prompts/`, `memory.py`, `state.py`.
- **LoRA 파이프라인**: `llm-trainer`(워커) — 콘텐츠 톤 튜닝 시 재사용 가능(선택).
- **외부연동 원형**: `market-feed`(②워커 + 부패방지 계층) — `research-feed`로 복제할 틀.

### ⚠️ 비어 있는 것 (설계가 반드시 결정)
1. **RAG 저장소 미배선** — `agent/rag/{retriever,embeddings}.py`는 **스텁**. `main.py`에서 `retriever=None`으로 주입, `docker-compose.yml`에 벡터DB **없음**, `pgvector` 주석처리. → CONVEY의 "리서치 원문 검색"이 핵심인데 저장소가 미정. **아키텍처 최대 결정.**
   - config 기본값: `embedding_model=nomic-embed-text`(Ollama), `vector_top_k=4`.
2. **파이프라인 트리거 모델** — 무엇이 파이프라인을 시작하나(수동 API? 스케줄? 소스도착 이벤트?), 동기 vs 비동기. 원형은 요청-응답 + Kafka 둘 다 가능하나 CONVEY 흐름은 미정.
3. **research 입력 정의** — 소스 유형(웹/RSS/PDF/API…)·수집 방식(pull vs push)·규모·빈도.
4. **content 산출물 정의** — 콘텐츠 유형(블로그/요약/뉴스레터/SNS…)·포맷·길이·톤·구조. 1:N/N:1 관계.
5. **생성 방식** — 단발 vs 멀티스텝(요약→구성→초안→다듬기), 사람 개입 지점(초안 검토/편집).
6. **모델 선택** — 한국어 콘텐츠 품질(기본 `llama3.2`로 충분한가), LoRA 톤 튜닝 필요 여부.
7. **publishing 채널** — 대상 채널(Notion은 MCP 미승인 상태)·발행 승인 워크플로우 구현.
8. **사용자/규모** — 단일 사용자(본인) vs 팀 vs 다중 테넌트. auth 활용 수준·동시성.

## 확인 필요 (설계 질문으로 전환 — 아래 대화에서 사용자에게 질의)
위 ⚠️ 8항목 전부. 특히 (1) RAG 저장소, (2) 트리거 모델, (3~4) 입출력 정의가 나머지를 좌우함.

---

## 설계 입력 확정 (2026-07-18 — 사용자 문답)

| # | 항목 | 결정 |
|:--|:---|:---|
| Q1 | 트리거 | **둘 다** — 사람 요청(on-demand) + 소스 도착 자동 |
| Q1b | 실행 모델 | **비동기 작업 큐**(Kafka 잡) |
| Q2 | RAG 저장소 | **Postgres + pgvector**(기존 DB 재사용). 임베딩 로컬 `nomic-embed-text` |
| Q3 | 리서치 소스 | **RSS/뉴스 피드 + 외부 API** |
| Q3b | 산출물 | **쇼츠 영상 + 이미지 (둘 다 동등)** ← 텍스트 아님, 멀티미디어 |
| Q4 | 생성 위치 | **혼합** |
| Q4b | 외부 API | **이미지·TTS·영상클립 = 외부 API** / 텍스트·임베딩 = 로컬 Ollama / 영상합성 = 로컬 ffmpeg |
| Q5 | 사람 개입 | **최종 산출물만 승인** (스크립트~영상 전자동, 완성본 검토 후 발행) |
| Q6 | 언어·모델 | **한국어, 기본 llama3.2로 시작**. LoRA(llm-trainer)는 휴면 |
| Q7 | 발행 채널 | **YouTube Shorts** (업로드 API + OAuth) |
| Q8 | 사용자·규모 | **미정** → 단일 사용자 기준 단순 설계, 확장 여지만 남김 |

## ⚠️ 큰 전환 — 텍스트 파이프라인 → 멀티미디어 파이프라인
원형(py-msa-ai)은 텍스트 LLM 중심. **쇼츠/이미지 생성**은 별도 미디어 서비스가 필요.
다만 **미디어 생성을 외부 API로** 결정 → 무거운 로컬 GPU 서비스 대신 **외부 API 래퍼 서비스**(market-feed의 부패방지 계층 패턴 재사용)로 가볍게 확장 가능 → **원형 골격은 여전히 유효**(MSA·게이트웨이·비동기 Kafka·서비스별 DB·워커).

## 가드레일 정제 (반영 필요 — CLAUDE.md §4)
기존 "외부 LLM API 금지 — 로컬 Ollama만"을 **텍스트 한정**으로 좁힘:
- **텍스트/스크립트 LLM·RAG 임베딩**: 로컬 Ollama만 (원문 데이터 보호 유지)
- **미디어 생성(이미지·TTS·영상클립)**: 외부 API 허용
- **발행**: YouTube Shorts 자동 게시는 **사람 승인 후에만**(자동 발행 금지 유지)

## 목표 아키텍처 (서비스 맵 — 설계 대상)

| 서비스 | 형태 | 역할 | 출처 |
|:---|:---|:---|:---|
| `gateway`·`auth` | ①API | 단일 진입·JWT | 원형 유지 |
| `llm-inference` | ①API | 스크립트/카피 생성(로컬 Ollama) | 원형 유지 |
| `agent` | ①API | RAG(리서치)+스크립트 오케스트레이션 | 원형 유지·확장 |
| `research` | ①API | 소스·원문·pgvector 임베딩 | sample-domain 복제 |
| `research-feed` | ②워커 | RSS 폴링 + 외부 API 수집 → Kafka | market-feed 복제 |
| `content` | ①API | 생성 잡·스크립트·미디어 조립 상태 | sample-domain 복제 |
| `image-gen` | ①API/워커 | 외부 이미지 API 래퍼 | 신규(부패방지 계층) |
| `tts` | ①API/워커 | 외부 TTS API 래퍼 | 신규(부패방지 계층) |
| `video-clip` | ①API/워커 | 외부 영상생성 API 래퍼 | 신규(부패방지 계층) |
| `video-assembly` | ②워커 | ffmpeg 합성(이미지+음성+자막→mp4) | 신규(로컬 CPU) |
| `publishing` | ①API | YouTube Shorts 업로드·승인 | sample-domain 복제 |
| `llm-trainer` | ②워커 | (휴면) 향후 LoRA 톤 학습 | 원형 유지 |

**파이프라인(안)**: `research.ingested` → `content.generate` → (스크립트) → `image.generate`·`tts.generate`·`video.clip` → `video.assemble` → `content.ready` → (사람 승인) → `content.published`(YouTube)

## 후속 — durable 승격 (2026-07-18 반영 완료 ✅)
- ✅ 목표 아키텍처·가드레일 정제 → `CLAUDE.md` §1·§4·§6 + `doc/ref/architecture/README.md` 반영
- ✅ 미디어 서비스·도메인 경계 → `doc/ref/domains/{research,content,publishing}.md` 갱신. **결론: 4번째 media 도메인 두지 않음** — 미디어 워커는 무상태, 자산·완성본 상태는 `content`가 소유
- ✅ 콘텐츠/소스/미디어 용어 → `doc/ref/glossary/terms.md` 신설
- ✅ 프로젝트 결정 기록 → `doc/decisions/0001~0003` (멀티미디어 전환·pgvector·가드레일 정제)

## 다음 단계 → `/design` (코어 라운드)
확정: **코어부터 단계적**. 1라운드 설계 대상 = `research`(+pgvector) · `research-feed`(RSS/외부API) · `content`(스크립트·잡 상태) · `agent` RAG 배선. 미디어(`image-gen`·`tts`·`video-clip`·`video-assembly`)·`publishing`(YouTube)은 후속 라운드.
