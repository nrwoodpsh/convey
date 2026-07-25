# CONVEY 2차 개발 — 계획 + 시스템 전체 분석·학습 가이드 (2026-07-24 확정)

> **이 파일 하나가 2차의 전부**: 위쪽 = 2차 정의·마일스톤(M1~M4), 아래쪽 = M1의 작업 문서(시스템 전체 분석·학습 가이드 8항목 + 진행 체크리스트).
> **진행 방식**: M1 체크리스트를 **위에서부터 한 항목씩** — ① 학습(이 문서로 이해) → ② 개선 제안(사용자) → ③ 설계/수정/구현(`/design→/builder→/sync→/commit`) → ④ 상태 갱신. **한 번에 몰아 하지 않는다.**
> 코드가 이 문서와 다르면 코드가 정본(발견 시 문서 정정).

---

# 1부. 2차 정의 & 마일스톤

## 0. 2차의 성격 (사용자 확정)

**"시스템의 구동 원리를 파악하며 개선한다."** 개선이 목적이자, 동시에 **사용자가 이 시스템·그래프DB·Kafka 이해도를 높이는 과정**. 그래서 2차의 첫 마일스톤은 "코드를 더 짜기"가 아니라 **"어떻게 동작하는지 파고들고, 그 이해로 바꿀 지점을 제안"**하는 것.

**작업 모드**: 탐색적 대화 — 사용자 질문 → 내가 실제 코드 기준 설명 → 사용자가 수정 제안 → flow로 반영. 일반론이 아니라 이 리포의 진짜 로직으로. 코드가 예상과 다르면 정직하게.

## 마일스톤

- **M1. 구동 원리 파악 & 개선 (핵심·먼저)** — 아래 2부(시스템 분석·학습 가이드)를 항목별로 하나씩 진행. 핵심 알고리즘 이해 + 거기서 나온 약점 개선(품질 향상 포함) + 그래프DB·Kafka 습득.
- **M2. 관리 대시보드 리디자인** — **[설계 ✅ ㊵]** `content/20260725-task-dashboard-redesign.md`. 탭(오늘자·쇼츠·설정)+설정(admin 중계)+근거·품질 지표.
- **M3. 필요 기능 추가** — **[M1 개선 설계에 흡수]** 온톨로지(㉟)·템플릿(㊳)·수집(㉝)·배경(㊴) = 발견된 필요 기능. 새 기능 나오면 그때 설계.
- **M4. YouTube + 인증 연결** — **[설계 ✅ ㊶]** `publishing/20260725-task-publish-youtube.md`. YouTube 발행(승인 후·private)+Supabase 활성화+대시보드 노출 정리. 외부 키는 사람 게이트.

**(참고) 2차 범위 밖 — 필요 시**: 클라우드 배포·모니터링 · 스토리지(MinIO/S3) · 미디어 볼륨 정책 · 전체 종목 마스터(pykrx). `backlog-deferred.md`.

**리스크·메모**: qwen3:14b 느림(추론모델·think=False로 완화, ADR 0015) · M1은 항목별 "이해→(필요시)검증→개선 1~2개"로 잘게 · 모든 개선은 flow 경유(드리프트 방지).

---

# 2부. M1 시스템 전체 분석·학습 가이드

## 진행 체크리스트

| # | 항목 | 학습 | 개선 도출 | 설계/구현 | 비고 |
|:--|:--|:--:|:--:|:--:|:--|
| 1 | 전체 아키텍처 | ✅ | — | — | 지도 |
| 2 | 기사 수집 기준 | ✅ | ✅ | ▶ | 오태깅 수정 설계(㉜) |
| 3 | 엔티티(노드) 추출 | ✅ | ✅ | ▶ | 타입검증(㉞) → ㉟에 흡수 |
| 4 | 릴레이션 규칙 | ✅ | ✅ | ▶ | 엣지 오용 → ㉟(온톨로지+domain/range) |
| 5 | Kafka 이벤트 흐름 | ✅ | ✅ | ▶ | 정석 스택 설계(㊱: 봉투·Avro·Debezium·DLQ·Grafana) |
| 6 | GraphRAG 회수 & 이슈 선별 | ✅ | ✅ | ▶ | news_count 중복 수정(㊲) + 시나리오 템플릿(admin) |
| 7 | 영상 생성 규칙 | ✅ | ✅ | ▶ | 배경 전략(라이브러리·생성·Pexels)+가독성 패널(㊴) |
| 8 | 게이트웨이·보안 | ☐ | ☐ | ☐ | |

> 상태: ☐ 미착수 / ▶ 진행 / ✅ 완료. 항목 진행하며 갱신.

---

## §1. 전체 아키텍처 (지도)

**한 문장**: CONVEY = "리서치 원료 → 유튜브 쇼츠"를 만드는 **조립 라인**. 공정(단계)으로 나뉘고, 각 공정이 작은 독립 서비스(MSA), 공정 사이는 **Kafka**(컨베이어)로 넘긴다.

### 3단계 척추
```
[1] 축적            [2] 선별              [3] 제작
시세·뉴스 모으기  →  오늘 뭘 만들지 고르기 →  대본→음성·차트→영상
```

### 지도
```
[1] 축적  market-feed(시세) ┐            ┌ research: Neo4j(관계) + Postgres(사실)
          news-feed(뉴스)  ─┼─(Kafka)─▶─┤   ← 개방형 NER로 노드·관계 추출
                            └───────────┘
[2] 선별  issue-detector ◀─(Kafka)─ → issue.selected(오늘의 이슈 종목)
[3] 제작  content(잡·상태) ─ agent(근거 대본, GraphRAG)
             ├─(Kafka: media.assemble)▶ video-assembly(차트·수치·자막·ffmpeg) → mp4
             └─ (사람 승인) ▶ publishing ▶ YouTube
공용:  gateway(정문·인증·라우팅) · llm-inference(로컬 Ollama qwen3:14b) · Kafka(버스)
```

### 두 개의 뇌
| Neo4j(그래프) | Postgres(표) |
|:--|:--|
| 관계 — 무엇이 무엇과 엮였나(삼성전자—[경쟁]→SK하이닉스) | 사실 — 정확한 값·원문(종가 71,900) |
| 인과 설명(알파①) | 정확한 수치(알파③) |

대본은 **둘을 합쳐** 만든다(관계 + 수치). RAG는 GraphRAG+SQL(벡터 없음 — ADR 0006).

### 저장 DB 소유 (Database per Service — 남의 DB 직접접근 X)
| 서비스 | 소유 DB | 담는 것 |
|:--|:--|:--|
| research | **Neo4j**(research_graph) + **research_db**(PG) | 관계(그래프) + 시세·기사(사실) |
| content | **content_db**(PG) | 잡·대본·자산·완성본 상태 |
| publishing | **publishing_db**(PG) | 발행 기록·상태(멱등·재시도) |
| 그 외(agent·llm-inference·feeds·issue-detector·video-assembly·gateway) | 없음 | 필요 시 남 서비스에 질의 |
> PG 3종은 한 Postgres 컨테이너 안의 별도 논리 DB(서로 안 넘봄). Neo4j는 별도 컨테이너.

### 통신 3종 (크기가 아니라 "성격"으로 고름)
| 수단 | 언제 | 예 |
|:--|:--|:--|
| **Kafka 이벤트** | 사건 핸드오프(파이프라인 흐름) — 기본 | 기사 전달·이슈 선별·합성 요청 |
| **HTTP 요청/응답** | 질의(답 받아야 진행)·외부 진입 | agent→research 조회, 바깥→gateway |
| **공유 볼륨 + 경로** | **대용량 바이너리**(Kafka에 못 담음) | mp4·broll → 볼륨에 두고 경로만 이벤트에 |
> HTTP는 데이터가 커서가 아니라 "답을 받아야 다음 진행"이라 씀. 진짜 대용량(영상)은 볼륨+경로.

### 한 기사의 여행
```
연합 RSS → news-feed(수집·태깅) →(research.ingested)→ research(PG 원문 + Neo4j NER)
 → issue-detector(이슈 판단) →(issue.selected)→ content(잡) → agent(근거 대본)
 →(media.assemble)→ video-assembly(합성) → mp4 → 사람 승인 → publishing → YouTube
```

**개선 후보(§1)**: 아키텍처 자체는 안정 — 개선은 하위 항목에서.
**상태**: 학습 ✅ (2026-07-24)

---

## §2. 기사 수집 기준 (news-feed)

### 동작
- 워커(`services/news-feed/app/worker.py`)가 **두 루프** 동시 실행:
  - 뉴스·공시 루프 **300초(5분)** → `research.ingested`
  - 거시 루프 **86,400초(1일)** → `research.macro`(수치, 기사 아님)
- 소스 4종(`external_client.py`):

| 소스 | 무엇을 | 얼마나 | body | 라이선스 |
|:--|:--|:--|:--|:--|
| RSS(5개: 연합·한경·매경·이데일리·서울경제) | 경제 피드 | 피드당 최신 10건(최대 50) | `summary`(발췌) | RSS |
| Naver 뉴스검색 | **사전 종목명으로 타깃 검색** | 종목당 10건 | `description`(발췌) | NAVER |
| DART | 최근 공시 | 20건 | `report_nm`(제목) | DART |
| ECOS·FRED | 거시 지표 | 지표별 1건 | (수치) | ECOS/FRED |

- **필터는 사실상 하나**: `source_url` 없으면 버림(무출처 금지, 알파1). **날짜·중요도 필터 없음**(최신순).
- 수집 후 태깅(`tagging.py`) 붙여 발행(`key=source_url`): `tickers`·`entities`(사전 기반, 환각 0) + `event_hints`(키워드 실적/공시/급등락).
- **중복**: 수집엔 dedup 없음(매 5분 재발행) → research가 `source_url` 멱등으로 거름.

### 핵심 규칙
- 본문은 **전문 아님(발췌/요약)** — 소스가 주는 요약문. (릴레이션 깊이에 영향 → §3·§4)
- Naver는 **사전 종목만 능동 검색** — 사전 밖은 RSS 우연 유입.

### 개선 후보
1. 본문 발췌뿐 → 전문 크롤링 도입 여부(저작권·부하 트레이드오프).
2. 날짜 필터 없음 → "오늘자"를 수집 단계에서 거를지.
3. Naver 사전 종목 한정 → 사전 확대(전 KRX)·키워드 검색 추가.
4. 피드당 10건·5분·언론사 고정 → 조정.
5. 최신순만 → 수집 우선순위 부여 여부.

**검증 결과(2,898건 실측)**: 종목 태깅률 82.4% · 소스는 **네이버 83% 지배**(사전 46종목 검색) · RSS 172뿐. **버그 확인**: `tag_tickers`가 본문 스침까지 태깅 → "보일러 기사→카카오(카카오톡)", "빙수 기사→카카오(저당카카오)" 오태깅. → 라운드㉜로 수정 설계.

**상태**: 학습 ✅ / 개선도출 ✅(오태깅 검증) / 구현 ▶ (설계 `research/20260724-task-tagging-scope.md`)

---

## §3. 엔티티(노드) 추출 (research)

### 동작 (`services/research/app/extract/relations.py` `extract_graph` / `extract_article_graph`)
- 신규 기사 1건 → **개방형 NER**(로컬 Ollama 1콜)로 `{entities, relations}` 추출.
- 긴 본문(>1,500자)은 **요약 선행**(㉛, ADR 0015) 후 요약 위에서 NER, 검증은 원문.
- **환각컷**: LLM이 뽑은 엔티티는 **본문(원문)에 실제 문자열로 있어야** 채택(`raw in verify`). 없으면 폐기.
- **정규화/필터**: 공백·괄호 제거(`_normalize_entity`), 스톱워드(`ENTITY_STOPWORDS`: 정부·시장·기업…), 최소 길이 2.
- **seed 합집**: news-feed가 붙인 사전 엔티티(고정확)는 검증 없이 신뢰하고 합침.
- 저장: `neo4j_repo.upsert_entity` — 모든 노드 `:Entity`, 아는 종목이면 `:Stock`+`ticker` 라벨 추가.

### 핵심 규칙
- 노드로 남으려면: **(본문 실재 ∧ 스톱워드 아님 ∧ 길이≥2) ∨ 사전 seed**.
- 텍스트 LLM은 **로컬 Ollama만**(원문 보호), 수치는 만들지 않음.

### 개선 후보
1. **entity linking 부재** — "삼성"/"삼성전자"/"삼성전자(주)"가 별개 노드. 동의어 병합.
2. 엔티티 **타입 라벨 없음**(전부 `:Entity`) — `:Person`·`:Event`·`:Org` 부여.
3. 요약 경로에서 관계 회수 감소 가능(요약이 짧아서) → threshold·num_predict·num_ctx 튜닝.
4. 스톱워드가 최소 — 노이즈 노드 관측 후 확장.

**검증 결과(라이브)**: 엔티티 5,580(종목 47). 비종목에 섹터+개방형(젠슨황). **버그**: "노조·노사·이동통신사"가 노드로(스톱워드 19개뿐 + LLM 반환 타입 미활용). → 라운드㉞ 설계(타입 검증 + 스톱워드 보강).

**상태**: 학습 ✅ / 개선도출 ✅ / 구현 ▶ (설계 `research/20260724-task-extract-quality.md`)

---

## §4. 릴레이션 규칙 (research)

### 동작 (같은 `relations.py` + `neo4j_repo.upsert_relation`)
- 관계 = `(subject)-[edge]->(object)`, **엣지 5종만**: `HAS_EVENT`·`AFFECTS`·`SUPPLIES`·`COMPETES`·`BELONGS_TO`(`EDGE_TYPES` 화이트리스트).
- **채택 조건**: subject·object가 **둘 다 검증 엔티티∪seed에 있고**, edge가 화이트리스트일 때만.
- **근거 결속(가드레일)**: 모든 관계에 `source_article_id` 부착(`SET r.source_article_id`). 무출처 관계 불가.
- **결정론 엣지**(LLM 미개입, `consumer.py`): 종목→섹터 `BELONGS_TO`(㉕), 종목→사건 `HAS_EVENT`(㉙, event_hints/DART).
- 화이트리스트 밖 edge는 `upsert_relation`이 `ValueError`(주입·오타 차단).

### 핵심 규칙
- 관계는 **좁고 검증된 것만**(5종·양끝 검증·근거 필수). LLM 자유 서술 금지 → 환각 0(알파1).
- 회수 시 `relations_of(name, hops=1..3)`로 다홉 추론(`neo4j_repo`).

### 개선 후보
1. 엣지 5종이 충분한가 — 부족한 관계 유형(예: 자회사·인수·규제) 추가 여부.
2. 관계 방향/강도(가중치) 없음 — 필요 시 속성 추가.
3. 결정론 엣지와 LLM 엣지의 우선순위·중복 정리.
4. 다홉 회수의 관련성 랭킹(지금 LIMIT만).

**검증 결과(라이브)**: 엣지 SUPPLIES 1,884·BELONGS_TO 1,620·AFFECTS 1,139·HAS_EVENT 956·COMPETES 392. 삼성전자 경쟁사 대체로 정확(SK하이닉스·ASML·엔비디아)하나 **"COMPETES 노조/노사/이동통신사" 오염** — §3 엔티티 오염이 뿌리. → ㉞(엔티티 정화)로 자동 해결.

**상태**: 학습 ✅ / 개선도출 ✅(§3와 공동) / 구현 ▶ (㉞)

---

## §5. Kafka 이벤트 흐름

### 동작
- 서비스 간 결합을 끊는 **이벤트 버스**. 토픽(관문) 목록 = 파이프라인 단계:

| 토픽 | 발행 → 소비 |
|:--|:--|
| `market.ticks` | market-feed → research·issue-detector |
| `research.ingested` | news-feed → research·issue-detector |
| `research.macro` | news-feed → research |
| `issue.selected` | issue-detector → content(자동 양산) |
| `content.generate` | content → content consumer |
| `media.assemble` | content → video-assembly |
| `content.assembled` | video-assembly → content(fan-in) |
| `content.ready`/`content.approved` | 완성(내부)/사람 승인 → publishing |

- 오프셋(커서)로 재개, 컨슈머 그룹으로 분산, 랙(밀림)으로 병목 관측. 상세 학습: `doc/ref/graph-kafka-guide.md`.
- 멱등: news-feed 재발행 → research가 `source_url`로 걸러 중복 방지.

### 개선 후보
1. 랙/모니터링 가시화(대시보드 M2와 연계).
2. 실패 메시지 처리(DLQ·재시도 정책) 정형화.
3. 아웃박스 신뢰성 점검(커밋-발행 원자성).

**상태**: 학습 ☐ / 개선 ☐ / 구현 ☐

---

## §6. GraphRAG 회수 & 이슈 선별

### 회수 (agent → research `/search`)
- agent는 저장소 직접접근 없이 **research `/search`를 east-west HTTP(HMAC 서명)**로 호출(`services/agent/app/rag/retriever.py`).
- `Evidence` = `price`(시세) + `facts`(기사) + `macros`(거시) + `relations`(그래프 관계). 대본은 이 근거로만 문장 생성(수치는 데이터, 관계는 그래프).
- 그래프 회수는 research 내부 `relations_of`(Cypher 다홉) + Postgres SQL.

### 이슈 선별 (issue-detector)
- `RollingRanker`가 24시간 창에서 종목 점수화:
  `score = w_change·|등락률| + w_volume·volume_z + w_news·news_count` (`ranking.py`).
- 상위 이슈 중 **score ≥ 0.5**만 `issue.selected` 발행(무의미 양산 방지) → content 자동 생성(알파2·4).

### 개선 후보
1. 랭킹 가중치(w_change/volume/news) 튜닝·근거 부족 종목 배제.
2. 회수 top_k·관련성 정렬·관계 우선순위.
3. 이슈 임계(0.5)·창(24h) 조정.

**상태**: 학습 ☐ / 개선 ☐ / 구현 ☐

---

## §7. 영상 생성 규칙 (video-assembly)

### 동작 (`services/video-assembly/app/{render,assemble,worker}.py`)
- **결정론 렌더**: matplotlib로 차트(한글 폰트 번들) + 수치 오버레이(팝·금색). **수치는 데이터에서만**(LLM 생성 0, 알파3).
- 구성: 인트로/아웃트로 카드 · 차트 베이스 + 수치 · 구간 자막 싱크(drawtext enable=between) · 신뢰 배지 · 배경 하드컷(concat) · 구간 TTS 병렬(edge-tts) · broll(Pexels).
- 합성은 로컬 ffmpeg(외부 영상생성 API 미사용).

### 개선 후보
1. 길이 튜닝(현 ~43s → 목표 30s).
2. 배경 anim 재시도 시 선택 유실 버그.
3. 연출(전환·타이포·리듬) 고도화.
4. broll 대용량 클립 합성 시간·파일크기 상한.

> 상세 렌더/합성 규칙은 이 항목 진행 시 `render.py`·`assemble.py` 재확인.
**상태**: 학습 ☐ / 개선 ☐ / 구현 ☐

---

## §8. 게이트웨이·보안

### 동작 (`gateway/app/{main,config}.py`)
- **단일 진입**: 외부 요청은 gateway(:8080)로만. 라우트 `/research`·`/content`.
- **인증**: Supabase **JWKS 검증**(ADR 0007). 로그인·발급은 Supabase, gateway는 검증만. 공개 경로 외 Bearer 필수.
- **HMAC 하류 신뢰헤더**(`libs/common/common/security.py`): 내부 서비스 직접호출 차단(east-west 서명).
- 대시보드(:8091)는 **예외** — gateway 우회 무인증 로컬 화면(ADR 0010).

### 개선 후보
1. Supabase 실계정 연결(M4).
2. 대시보드 8091 무인증 노출 정리(게이트웨이 뒤로 — M4).

**상태**: 학습 ☐ / 개선 ☐ / 구현 ☐

---

## 부록 A. 수집 재설계 합의사항 (대형 `/design` 입력 — 2026-07-24 확정)

§2 수집 + M2 대시보드 설정이 묶인 대형 설계의 **확정 방향**. ㉜(태깅 버그) 빌드 후 착수.

- **수집 = 넓게**: 종목 한정 X. 그날의 **경제·주식·사회·정치** 전반(놓치지 않는 커버리지).
- **관심/핫함 필터(운영자 설정, 체크박스)**:
  - **기본 = 코스피200 전체 ON**(baseline) + **키워드 등록**(정치·사회·테마) 추가 레이어.
  - 소스 on/off(네이버·RSS·DART) · 검색 기간(1주/1달/3달) · 중복 제거.
  - "핫함"은 issue-detector가 (코스피200 ∪ 등록 키워드) 매칭 기사 중 랭킹.
- **저장 = 전용 `admin` 서비스 + `admin_db` 신설(확정)**:
  - 테이블(예): `stock_master`(코스피200 시드 — 코드 46 승격) · `watch_stocks`(기본 전체 ON) · `watch_keywords` · `collection_sources` · `collection_period` · **`scenario_template`(시나리오 템플릿 — ㊳)** · **`background_asset`(배경 자산 라이브러리 — ㊴)**.
  - 대시보드(설정 메뉴)가 **쓰기**, news-feed·issue-detector가 **API로 읽기**(Database per Service 준수).
  - **ADR 기록 예정**(새 서비스·새 DB·설정 소유권).
- **소스 정정**: 네이버=검색(검색어 O) / **RSS=검색 아니라 전체 수신 후 필터** / DART=종목 `corp_code`별 조회(현재 전체 최근 20 → 종목별).
- **스케일**: 코스피200 네이버 다회 검색 → 주기·기간·배치로 API 한도 관리.

## 다음 액션
- **§1 전체 아키텍처**부터 하나씩. 각 항목: 이 문서로 학습 → 개선 제안 → 필요 시 `/design`. 진행하며 체크리스트 갱신.
- **수집 재설계(부록 A)**: ㉜ 빌드 후 대형 `/design`(admin 서비스·admin_db·대시보드 설정 UI). ADR 신규.
