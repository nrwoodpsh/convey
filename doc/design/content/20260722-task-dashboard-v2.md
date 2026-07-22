# 20260722-task-dashboard-v2.md

> 라운드 ㉔ (대시보드 배치·흐름 v2 — 탭 + 마법사 + 시나리오 템플릿 + 배경 선택).
> `20260722-task-dashboard-workflow.md`(㉓)의 흐름을 **탭 2개 + 단계별 마법사**로 재배치.
> 계약: `api-contract-dashboard.py`(확장). CONVEY 첫 화면(브라우저), 로컬 전용·무인증.

## 1. Requirements

- **결론**: 대시보드를 **상단 탭 2개**(`오늘자 기사` | `생성쇼츠`)로 나누고, `오늘자 기사`에서 기사를 골라 **단계별 마법사**로 제작한다: **① 기사 선택 → ② 시나리오 템플릿 선택 → ③ 시나리오 수정 → ④ 배경 선택·쇼츠 생성 → ⑤ 미리보기**. 시나리오에서 **출처 근거 표시는 제거**. 기사는 **항상 오늘자만** 표시. 배경은 **실사 | 애니메이션** 선택.
- **핵심 변화**(㉓ 대비):
  1. **탭 UI**: `오늘자 기사`(제작) / `생성쇼츠`(완료·실패 목록·미리보기).
  2. **템플릿 선택**: 속보형·분석형·스토리형 3종(구성·톤). agent가 템플릿별 구성·문체를 달리 생성.
  3. **시나리오 수정**: 생성된 섹션 텍스트를 사람이 편집 → 저장 → 그 텍스트로 영상(내레이션·자막). 수치(차트)는 사실 고정(알파3).
  4. **출처 제거**: 시나리오/미리보기에서 출처 목록 UI 삭제(데이터는 보존 — 가드레일 기록).
  5. **오늘자만**: `/ui/articles` 당일(window 1일)만. (폴백 확대 없음.)
  6. **배경 선택**: real(종목 산업 실사) | anim(Pexels 모션그래픽·추상). 승인 시 적용.
- **Acceptance Criteria**:
  - [x] AC1: 상단 탭 2개(`오늘자 기사`/`생성쇼츠`). `/ui/articles` 당일만(폴백 제거). **검증: 당일 삼성 기사.**
  - [x] AC2: 템플릿 선택 → `POST /ui/generate{template}` → `scenario_ready`. **검증: breaking job#24.**
  - [x] AC3: `GET`→편집→`PUT /ui/jobs/{id}/script`(200) 반영, 출처 UI 없음. **검증: hook "[수정됨]…" 반영.**
  - [x] AC4: `approve-scenario{background:anim}` → `ready`. **검증: content 18, broll=추상 스파이럴 모션그래픽.**
  - [x] AC5: 템플릿별 구성 다름. **검증: 속보=[hook,chart,fact](거시 없음) vs 분석=사실3+거시.**
  - [x] AC6: 다크 테마·마법사. **검증: 편집 텍스트가 영상 자막까지 반영(end-to-end).**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **수정 후 재생성 아님**: 시나리오 수정은 **텍스트만** 갱신(재-LLM 아님). 차트 수치는 `job.chart`(사실)에서 영상 렌더 — 편집으로 수치가 바뀌지 않음(알파3 보존).
  - **템플릿 회귀**: agent `build_script`에 template 분기 추가. 기본값 `analysis`가 **기존 동작과 동일**해야 회귀 0(자동양산도 analysis).
  - **오늘자 0건**: 당일 수집 없으면 목록 빔 — 안내 문구. (㉓의 7일 폴백 제거 — 사용자 "항상 오늘자만".)
  - **배경 전달 시점**: template은 생성(agent) 시, background는 **승인 시** 전달 → 새 컬럼 불필요(approve 요청 바디).
  - **편집 저장 경합**: 편집 저장(PUT)은 `scenario_ready`에서만 허용(합성 시작 후 잠금).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 템플릿 축**: 택함 = **구성·톤 3종**(속보/분석/스토리) / 기각 = 길이 3종·톤만 3종 / 사유 = 구성 차이가 체감 큼(사용자 확정). agent가 섹션 구성·문체 분기.
  - **결정 2 — 배경 애니**: 택함 = **Pexels 모션그래픽·추상 쿼리**(real=산업, anim=abstract motion) / 기각 = 로컬 ffmpeg 생성(새 렌더·품질한계) / 사유 = 기존 PexelsClient·ADR 0009 재사용(사용자 확정).
  - **결정 3 — 수정 범위**: 택함 = **섹션 텍스트 편집(내레이션·자막용), 차트 수치 고정** / 기각 = 전면 재생성·수치까지 편집 / 사유 = 알파3(정확 수치) 보존 + 사람 편집은 문장만.
  - **결정 4 — 출처**: 택함 = **UI에서 제거(데이터 보존)** / 기각 = 완전 삭제 / 사유 = 사용자 요청은 표시 제거. 가드레일(무출처 기록)은 DB 유지.
  - **결정 5 — 배경 전달**: 택함 = **approve 바디의 background** / 기각 = 새 job 컬럼 / 사유 = 마이그레이션 회피·승인 시점에 필요.

## 3. UI/UX (다크 · 탭 · 마법사)

```
┌ CONVEY 운영 콘솔 (검정·레드·금색) ───────────────────────────┐
│  [ 오늘자 기사 ]  [ 생성쇼츠 ]     ← 상단 탭                    │
│──────────────────────────────────────────────────────────────│
│  ▷ 탭1: 오늘자 기사 (제작 마법사)                              │
│   1) 기사 목록(당일)  ○ 현대차 엘란트라…  005380  [진행]        │
│   2) 템플릿 선택   ( 속보형 ) ( 분석형 ) ( 스토리형 )           │
│   3) 시나리오 수정  ┌ 편집 가능한 섹션 텍스트 ─────┐ [저장]      │
│                     │ [훅] …  [차트] 현대차 종가… │            │
│                     └───────────────────────────┘  (출처 없음) │
│   4) 배경 선택 ( 실사 ) ( 애니 )   [ 쇼츠 생성 ▶ ]             │
│   5) 미리보기(생성 후 자동 재생)                               │
│                                                                │
│  ▷ 탭2: 생성쇼츠                                               │
│   [완료][실패][전체]  카드 그리드 → 클릭 시 상단 미리보기        │
└────────────────────────────────────────────────────────────────┘
```
- **마법사 단계 표시**(1→5) 진행바. 각 단계는 이전 완료 시 활성.
- 색·테두리(검정+레드+금색)는 ㉓ 유지. 미리보기는 마법사 5단계 + 생성쇼츠 탭 공용.
- 출처(근거 URL) **표시 안 함**(요청). 수치는 화면·영상에서 사실 그대로.

## 4. Logic

- **탭·마법사(FE)**: `static/index.html` 재구성 — 탭 전환, 마법사 상태(article→template→edit→background→preview). 폴링으로 `scenario_ready`→편집 노출, `ready`→미리보기.
- **오늘자 기사**: `/ui/articles` window_days=1 고정(폴백 제거). research `list_articles` 그대로.
- **템플릿(agent)**: `ScriptReq.template`(breaking|analysis|story) 추가. `build_script(..., template)` 분기 — 속보=hook+chart+fact 1, 분석=현행(hook+chart+fact 다수+macro), 스토리=hook(도입)+chart+fact(전개)+closing(전망, LLM). 기본 analysis(회귀 0).
- **생성(content)**: `/ui/generate`에 `template` → content.generate 이벤트에 실어 `handle_generate`가 `_call_agent_script(template)` 호출. auto=False(수동), scenario_ready 정지(㉓ 유지).
- **수정(content)**: `PUT /ui/jobs/{id}/script`(`ScriptEditReq`) → `service.update_script` → scenario_ready인 잡의 Script.sections 텍스트 갱신(kind 매칭, 차트 data_slots 보존). 아니면 CNT003.
- **승인+배경(content)**: `POST /ui/jobs/{id}/approve-scenario`(`ApproveScenarioReq.background`) → `approve_scenario(background)` → `media.broll_query(ticker, background)`로 assemble 이벤트. real=산업, anim=`abstract motion graphics loop`.
- **출처 제거(FE)**: ScriptView.citations 렌더 삭제(데이터는 계속 반환).

## 5. Implementation Split (다음 /builder)

- **agent**: `ScriptReq.template` + `build_script(template)` 분기(3종). 기본 analysis.
- **content**: `/ui/generate{template}`·`PUT /ui/jobs/{id}/script`·`approve-scenario{background}`·`service.update_script`·`approve_scenario(background)`·`_call_agent_script(template)`·`media.broll_query(ticker, background)`·`/ui/articles` 당일 고정. 스키마 `DashboardGenerateReq(+template)`·`ScriptEditReq`·`ApproveScenarioReq`.
- **FE**: `static/index.html` 탭 2개 + 마법사 5단계 + 배경 선택 + 출처 제거.

## 6. File Map (기계적)

- `[Mod] services/agent/app/main.py` — `ScriptReq.template` + 전달
- `[Mod] services/agent/app/script/builder.py` — template 분기(속보/분석/스토리)
- `[Mod] services/content/app/domains/content/ui_router.py` — generate(template)·PUT script·approve(background)
- `[Mod] services/content/app/domains/content/service.py` — update_script·approve_scenario(background)
- `[Mod] services/content/app/domains/content/media.py` — broll_query(ticker, background)
- `[Mod] services/content/app/consumer.py` — _call_agent_script(template)·handle_generate 전달
- `[Mod] services/content/app/domains/content/schemas.py` — DashboardGenerateReq(+template)·ScriptEditReq·ApproveScenarioReq
- `[Mod] services/content/app/static/index.html` — 탭·마법사·배경·출처 제거

## 7. Verification (다음 /builder)

- 템플릿 3종 각각 `/ui/generate` → `/ui/jobs/{id}/script` 구성 차이 확인(섹션 수·문체).
- `PUT script` 편집 저장 → 재조회 반영, scenario_ready 아니면 CNT003.
- `approve{background:anim}` → assemble broll 쿼리 anim → 영상 배경 모션그래픽(프레임 육안). real=산업 회귀.
- `/ui/articles` 당일만. 출처 UI 없음. 실 브라우저 마법사 1왕복(다크).

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 대시보드 v2 — 탭 2개(오늘자 기사/생성쇼츠) + 마법사 5단계(기사→템플릿→수정→배경→생성→미리보기). 시나리오 템플릿 3종(속보/분석/스토리, agent 분기, 기본 analysis 회귀0). 시나리오 수정(PUT, 텍스트만·수치 고정). 배경 real/anim(approve 바디, Pexels 쿼리). 출처 UI 제거(데이터 보존). 오늘자만(폴백 제거). 계약 확장(mypy 통과). ADR 불요(㉓ 0011 범위 — UX 배치·템플릿은 History로 충분). |
| 20260722 | /builder(수정) | 배치·안정화 후속: **가로 풀폭**(`.wrap` max-width 제거), 시나리오 수정 "멈춤" 보강(초안 생성 시 `editSections` 초기화·즉시 폴링·`editShownFor` 가드·"최대 30초" 안내), **미태깅 기사 `진행` 비활성화**(시세 근거 없으면 실패 방지), 대시보드 응답 `Cache-Control: no-store`(재빌드 시 옛 FE 캐시 방지). ops: `scripts/reset-data.sh`(잡·영상 초기화, `--all`/`--nuke`). 백엔드 계약 변경 없음. 실 스택 재현: 생성 30초→scenario_ready→시나리오 200 확인. |
| 20260722 | /builder | 구현·검증 완료(실 컨테이너 스택). agent `ScriptReq.template`+`build_script` 3종 분기(`_TEMPLATES`, 기본 analysis). content `_call_agent_script(template)`·`handle_generate` 전달·`start_generation(template)`·`update_script`(scenario_ready만)·`approve_scenario(background)`·`media.broll_query(ticker, background)`(anim=`abstract motion graphics loop`)·`/ui/articles` 당일 고정·스키마(`DashboardGenerateReq(+template)`·`ScriptEditReq`·`ApproveScenarioReq`)·ui_router(PUT script·approve body). FE 재작성(탭 2개·마법사 5단계·템플릿/배경 칩·편집 textarea·출처 제거). **검증**: 속보형 job#24 `[hook,chart,fact]`(거시 없음, 분석형과 구성 다름); `PUT script`→hook "[수정됨]…" 반영; `approve{anim}`→ready(content 18)→broll 추상 스파이럴 모션그래픽; 프레임 육안(제목·삼성전자(005930)·260,500원·+2.36%·**편집 자막 반영**). **이탈**: (1) 배경은 approve 바디 전달(새 컬럼 회피), (2) TDD DB 하니스 부재로 실 스택 검증, (3) 템플릿 기본 analysis=기존 동작(자동양산 회귀0). mypy·계약 통과. |
