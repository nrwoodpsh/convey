# 20260722-task-dashboard-workflow.md

> 라운드 ㉓ (대시보드 재설계 — 기사 기반 승인 워크플로우 + 다크 테마). ADR 0010·0011.
> `20260722-task-dashboard.md`(㉒)의 대시보드 골격을 **기사→시나리오→승인→생성** 흐름으로 재편.
> 계약: `api-contract-dashboard.py`(확장). CONVEY 첫 화면(브라우저), 로컬 전용·무인증.

## 1. Requirements

- **결론**: 대시보드를 **오늘자 수집 기사 목록 → 선택 → 진행 → 시나리오 제시 → 승인 → 쇼츠 생성** 흐름으로 재편한다. 근거(기사) 있는 것만 제작(자유 입력 제거 — 알파1 정합). 사람이 **영상 만들기 전에 시나리오를 승인**한다. 테마는 다크(검정+레드+금색), brandlogy 흔적 제거, 영상 미리보기는 **상단** 배치.
- **핵심 변화**:
  1. **기사 선택 전용**: `GET /ui/articles`(오늘자, research east-west) → 자유 입력 박스 제거.
  2. **승인 게이트**: 수동 잡은 `scripting → scenario_ready(승인 대기) → assembling → ready`. 승인 전엔 영상 합성 안 함. 자동양산(알파4)은 무정지 직행(결정 확정).
  3. **시나리오에서 종목코드 제외**: chart 문장을 `현대차 종가 …`(한글명)로 — 코드 낭독/노출 안 함(agent builder 수정).
  4. **테마**: 검정 배경 + 레드 + 금색. brandlogy 워드마크·용어 제거(제품명 CONVEY).
  5. **레이아웃**: 미리보기(영상) **상단**, 그 아래 제작(기사→시나리오→승인), 그 아래 내 쇼츠 목록.
- **Acceptance Criteria**:
  - [x] AC1: `GET /ui/articles` → 오늘자 수집 기사 목록. research east-west(HMAC). 폴백 7일. **검증: 실 기사 251건, 현대차·삼성 한글명.**
  - [x] AC2: 기사 선택 → `POST /ui/generate` → **초안 잡** `scenario_ready`(합성 안 함). **검증: job#22.**
  - [x] AC3: `GET /ui/jobs/{id}/script` → 시나리오 제시. **검증: chart "현대차 종가…"(코드 없음).**
  - [x] AC4: `approve-scenario` → `assembling`→`ready`. 아니면 CNT003(409). **검증: content 16, 재승인 409.**
  - [~] AC5: 자동양산 무정지 — auto=True 분기=기존 동작 보존(코드경로 검증). 신규 run은 dedup으로 미실시.
  - [x] AC6: 다크(검정+레드+금색)·brandlogy 제거·미리보기 상단. **검증: 실 스택 왕복, 영상 프레임.**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **오늘자 기사 데이터 유무**: 로컬 수집이 안 돌면 오늘자 기사 0건 → 목록 빈다. **폴백: window_days 확대(최근 N일)** + 빈 목록 안내. (수집은 news-feed/RSS·Naver — 별개 파이프라인.)
  - **east-west 인증**: content(무인증 /ui) → research(gateway·HMAC 보호)는 **HMAC 서명**으로 직접 호출(agent retriever 패턴). content가 `gateway_internal_secret` 보유(이미 consumer에서 사용).
  - **상태 분기**: handle_generate가 `auto` 플래그로 분기 — 자동=합성 직행, 수동=`scenario_ready` 정지. 플래그 누락 시 안전값(수동=정지)로.
  - **승인 2단계 혼동**: 이번 `approve-scenario`(영상 전, 신규)와 기존 `approve`(ready→approved→publishing, 발행 전, 연기됨)는 **다른 게이트**. 이름·상태로 구분.
  - **기사 종목 태깅**: Article.tickers(JSONB)에서 대표 1개. 없으면 종목 미지정(차트 근거 없어 실패 가능 — 태깅된 기사 우선 노출).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 진입**: 택함 = **기사 선택 전용**(자유 입력 제거) / 기각 = 자유 입력 병행 / 사유 = 근거 없는 생성 차단(알파1). (사용자 확정)
  - **결정 2 — 승인 게이트 범위**: 택함 = **수동만 시나리오 승인, 자동은 무정지** / 기각 = 전건 승인(알파4 자동양산 약화) / 사유 = 알파4 유지 + 사람이 만드는 건 검토. (사용자 확정)
  - **결정 3 — 상태머신**: 택함 = `scripting→scenario_ready→assembling→ready` (수동), 자동은 `scripting→assembling` 직행 / 기각 = 별도 draft 테이블 / 사유 = 기존 GenerationJob 상태 확장이 최소 변경.
  - **결정 4 — 기사 회수 위치**: 택함 = **research 신규 `GET /research/articles`** + content east-west 클라이언트 / 기각 = content가 research_db 직접(금지·경계 위반) / 사유 = 도메인 경계(수집·기사=research) + 저장소 직접접근 금지.
  - **결정 5 — 시나리오 코드 제외**: 택함 = **agent builder chart 문장을 한글명으로**(공유 `common.stocks`) / 기각 = 표시단에서 정규식 제거 / 사유 = 원천 수정이 내레이션(TTS)·자막·시나리오 모두 일괄 해결.
  - **결정 6 — 테마**: 택함 = **검정+레드(#C1001B 계열)+금색(#E9B44C)**, brandlogy 제거, 미리보기 상단 / 기각 = 화이트 브랜드(㉒)·사이버 네온 / 사유 = 사용자 지시. ADR 0011(테마·brandlogy 제거).

## 3. UI/UX (다크 · 미리보기 상단)

```
┌──────────────── CONVEY 운영 콘솔 (검정·레드·금색) ────────────────┐
│ ▶ 미리보기 (상단)                                                  │
│   ┌─9:16─┐  제목 · 종목명                                          │
│   │ 영상 │  시나리오(섹션+출처)                                     │
│   └──────┘                                                         │
│                                                                    │
│ ▶ 새 제작 — 오늘자 기사                                            │
│   ○ 현대차 3분기 어닝 서프라이즈…   005380 현대차   [진행 ▶]        │
│   ○ SK하이닉스 HBM 증설…            000660 …        [진행 ▶]        │
│   → 진행 시 초안(시나리오) 생성 → 아래에 시나리오+[승인] 노출        │
│   ┌ 시나리오 (job #22, 승인 대기) ─────────────────┐               │
│   │ [훅] …  [차트] 현대차 종가 416,500원 +4.39% …   │ [승인 → 생성] │
│   │ [사실] …  출처: krx.co.kr …                      │               │
│   └──────────────────────────────────────────────────┘             │
│                                                                    │
│ ▶ 내 쇼츠  [완료][실패][전체]  (카드, 클릭 → 상단 미리보기)         │
└────────────────────────────────────────────────────────────────────┘
```
- **색**: 배경 `#0c0c0e`, 패널 `#151518`, 레드 `#C1001B`(강조·상태), 금색 `#E9B44C`(제목·테두리 하이라이트), 텍스트 `#ece7de`.
- **테두리 강조(요구 유지)**: 금색 세선 보더 + 레드 상단 라인 + 상태 컬러 바.
- **흐름 상태**: 기사 선택→진행(POST generate)→폴링으로 `scenario_ready` 되면 시나리오+승인 노출→승인(approve-scenario)→폴링 `assembling`→`ready`→상단 미리보기 자동 재생.

## 4. Logic

- **research(신규 기사 목록)**: `repository.list_articles(window_days, limit)` → Article(id,title,source_url,published_at,tickers) 최신순. `service.list_articles` → `ArticleItem`(대표 ticker=tickers[0], name=stock_name). `router GET /research/articles`(gateway_user 보호). window 오늘(1일), 0건이면 호출측이 확대.
- **content 기사 클라이언트**: `research_client.fetch_articles(window_days)` — research `/research/articles` east-west 호출(HMAC 서명, agent retriever 패턴). `/ui/articles`가 이를 감싸 `ArticleListRes` 반환(오늘 0건이면 최근 7일 폴백 + 표시).
- **파이프라인 분기**: `ContentGenerateEvent`에 `auto: bool`. `start_generation(..., auto)` → 이벤트에 실어 발행. `handle_generate`: 스크립트 저장 후 `if auto: media.assemble 발행(assembling)` `else: status=scenario_ready`(정지). 자동경로(handle_issue)는 `auto=True`, 대시보드 `/ui/generate`는 `auto=False`.
- **승인**: `service.approve_scenario(job_id)` → `scenario_ready`만 통과(아니면 CNT003) → chart 근거로 `media.assemble` 발행 → `assembling`. (chart는 Script 저장 시 확보한 값 재사용 — Script/GenerationJob에 chart 보존 필요 → GenerationJob에 `chart JSON` 컬럼 추가(마이그레이션).)
- **시나리오(승인 전)**: `GET /ui/jobs/{id}/script` → `get_script_by_job` → `ScriptView`(chart 슬롯 채움). 완성본용 `/ui/contents/{id}/script`도 유지.
- **agent 코드 제외**: `builder.py` chart 문장 `"{ticker} 종가…"` → `f"{name} 종가 {{close}}원, 등락률 {{change_pct}}%"`(name=`stock_name(ticker)`, 없으면 접두 생략). 내레이션·자막·시나리오 일괄 코드 제거.
- **테마/레이아웃/brandlogy**: `static/index.html` 재작성(다크 검정+레드+금색, 미리보기 상단, 기사→시나리오→승인 흐름). `static/assets/brandlogy-*.png` 삭제, `/assets` 마운트 제거(또는 유지하되 미사용). 헤더 텍스트 = CONVEY.

## 5. Implementation Split (다음 /builder)

- **research(BE)**: `repository.list_articles` + `service.list_articles` + `router GET /research/articles` + schema(`ArticleItem`/`ArticleListRes`).
- **content(BE)**: `research_client.py`(east-west) + `/ui/articles`·`/ui/jobs/{id}/script`·`POST /ui/jobs/{id}/approve-scenario` + `service.approve_scenario` + `start_generation(auto)` + `handle_generate` 분기 + `handle_issue(auto=True)` + `JobStatus.SCENARIO_READY` + `GenerationJob.chart`(마이그레이션) + `DashboardGenerateReq`(기사기반)·`ArticleItem/ListRes` 스키마.
- **agent(BE)**: `builder.py` chart 문장 한글명화(`common.stocks`).
- **FE**: `static/index.html` 재작성(다크·상단 미리보기·기사→시나리오→승인), brandlogy 자산 제거.

## 6. File Map (기계적)

- `[Mod] services/research/app/domains/research/{repository,service,router,schemas}.py` — 기사 목록
- `[New] services/content/app/research_client.py` — research east-west(HMAC)
- `[Mod] services/content/app/domains/content/ui_router.py` — /ui/articles·/ui/jobs/{id}/script·approve-scenario
- `[Mod] services/content/app/domains/content/service.py` — approve_scenario·start_generation(auto)
- `[Mod] services/content/app/domains/content/schemas.py` — SCENARIO_READY·ArticleItem/ListRes·DashboardGenerateReq(기사기반)
- `[Mod] services/content/app/domains/content/models.py` + `alembic/versions/*` — GenerationJob.chart(JSON)
- `[Mod] services/content/app/consumer.py` — handle_generate 분기(auto)·handle_issue(auto=True)
- `[Mod] services/agent/app/script/builder.py` — chart 문장 한글명(코드 제외)
- `[Mod] services/content/app/static/index.html` — 다크 테마·상단 미리보기·워크플로우
- `[Del] services/content/app/static/assets/brandlogy-*.png` + `[Mod] main.py`(/assets 정리)

## 7. Verification (다음 /builder)

- research `list_articles` window/limit·정렬 단위 검증(가능 시). `/research/articles` east-west 200.
- `POST /ui/generate` → 초안 잡 `scenario_ready`(합성 미발행) 확인. `approve-scenario` → `assembling`→`ready`.
- 자동양산(issue.selected) → 승인 없이 `ready`(무정지) 회귀 확인.
- 시나리오 chart 문장에 **종목코드 없음**(한글명) 확인(실 스크립트).
- 실 컨테이너: localhost:8091 기사→진행→시나리오→승인→상단 미리보기 재생(다크 테마·brandlogy 없음). mypy·계약 통과.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /builder | 구현·검증 완료(실 컨테이너 스택). research `GET /research/articles`(repository·service·router·schemas) — 실 수집 기사 251건 회수. content `research_client`(east-west HMAC)·`/ui/articles`·`/ui/jobs/{id}/script`·`approve-scenario`·`service.approve_scenario`·`start_generation(auto)`·`handle_generate` 분기·`handle_issue(auto=True)`·`JobStatus.SCENARIO_READY`·`GenerationJob.chart`(Alembic c1d2e3f40011, 적용 확인)·`media.py`(공용 헬퍼 분리). agent `builder` chart 문장 한글명. FE 재작성(다크 검정+레드+금색, 미리보기 상단, 기사→시나리오→승인). brandlogy 자산 삭제·`/assets` 마운트 제거. **검증**: `/ui/articles` 실 기사(현대차·삼성 한글명); job#22 기사선택→**scripting→scenario_ready(합성 안 함)**→시나리오(chart "**현대차 종가…**" 코드 없음)→**approve→assembling→ready**(content 16)→재승인 **CNT003(409)**; 영상 프레임 육안(제목·현대차(005380)·수치·자막·공장배경). **이탈**: (1) TDD DB 테스트는 여전히 하니스 부재로 실 스택 검증 대체(관례), (2) 자동양산(AC5)은 auto=True 분기=기존 동작 보존 — 신규 run은 dedup으로 미실시(코드경로 검증), (3) 영상 시각 라벨은 한글명(코드) 유지(㉒ 사용자 요청), 시나리오·내레이션만 코드 제외. mypy·계약 통과. |
| 20260722 | /design | 대시보드 재설계 — 기사 선택 전용 → 시나리오 승인 게이트(수동만) → 생성. research `GET /research/articles`(east-west) 신규. 상태머신 `scenario_ready` 추가, `GenerationJob.chart` 보존. agent chart 문장 한글명(코드 제외). 다크 테마(검정+레드+금색)·brandlogy 제거·미리보기 상단. 자동양산 무정지 유지(확정). 계약 확장(mypy 통과). ADR 0010(대시보드)·신규 0011(테마·brandlogy 제거) 제안. |
