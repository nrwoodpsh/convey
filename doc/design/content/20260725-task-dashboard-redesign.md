# 20260725-task-dashboard-redesign.md

> 라운드 ㊵ (M2 — 운영 대시보드 리디자인). ADR 0010 확장.
> 계약: `api-contract-dashboard-redesign.py`. content 서비스(:8091). admin(㉝·㊳·㊴) API 중계.

## 1. Requirements
- **문제**: 현 대시보드는 "기사→시나리오→쇼츠" 생성 흐름 위주. M1에서 만든 **운영자 설정**(종목·키워드·소스·기간·템플릿·배경)을 넣을 곳이 없고, **근거(관계·출처)·품질 지표**도 화면에 부족.
- **목표**: 정보구조 개편(오늘자·쇼츠·**설정** 탭) + 설정 화면(admin 연동) + 근거 노출 + 품질 지표. 기존 생성 마법사는 유지·정돈.
- **Acceptance Criteria**:
  - [x] AC1: 상단 탭 3개 — **오늘자 기사 · 생성 쇼츠 · 설정(신규)**. **검증: 탭 전환·렌더.** — **P2 완료**(설정 탭 추가, maintab 3개·탭 토글). FE 셸에 `data-tab="settings"`·`#tab-settings` 확인.
  - [x] AC2: **설정 탭** — 종목/키워드/소스/기간(㉝)·시나리오 템플릿(㊳)·배경 자산(㊴)을 CRUD. content가 admin API 중계. **검증: 설정 변경 → admin_db 반영.** — **완료**(P1 백엔드 `/ui/settings/{tab}` + P2 폼 UI). 설정 서브탭 6종(종목 체크·키워드 추가/삭제/토글·소스 토글·기간 select·템플릿 노브 편집·배경 등록/삭제). 라이브: 설정 조회·키워드 왕복·period `/_` PUT·템플릿 PUT·배경 POST/DELETE 모두 200.
  - [x] AC3: **근거 뷰** — 시나리오/완성본에 관계(그래프)·출처 URL·수치 노출. **검증: job의 evidence에 relations·sources 표시.** — **완료**(P1 `GET /ui/jobs/{id}/evidence` + P2 근거 패널). 시나리오 편집(step3)·완성본 미리보기에 `renderEvidence`로 관계·출처(링크)·수치 표시. 라이브 job49: 관계 2·출처 8·수치 슬롯 치환.
  - [x] AC4: **품질 지표** — 그래프 노드·관계·오늘자 기사·이슈·완성 잡 수. **검증: 홈에서 지표 표시.** — **완료**(P1 `GET /ui/metrics` + P2 지표 카드). 상단 지표 스트립(`#metrics`) 5카드(그래프 노드·관계·오늘 기사·오늘 이슈·완성 쇼츠), `loadMetrics`가 init·오늘자 탭 전환 시 갱신. 라이브: 노드 12531·관계 13907·이슈 10·완성 잡 32.
  - [x] AC5: 기존 마법사(시나리오 승인·배경 선택) 흐름 유지(회귀 없음). 무인증 로컬(ADR 0010) 유지. — 기존 라우트 불변, 신규 라우트만 추가. content 회귀 통과, /ui 무인증 유지.

## 2. 핵심 결정 & 사각지대
- **결정 1 — 설정은 admin이 원천, content는 중계**: 대시보드가 admin API를 east-west(HMAC)로 읽어 표시(Database per Service). content가 admin_db 직접접근 X.
- **결정 2 — 근거 노출 강화**: 관계·출처를 화면에 보여 알파①(신뢰) 가시화. agent Evidence(§6)를 대시보드로.
- **사각지대**: admin(㉝)·템플릿(㊳)·배경(㊴) 선행 필요(설정 대상 존재). 무인증이라 M4 전엔 로컬만. 배경 업로드 UI(대용량→볼륨). 화면 상세(레이아웃·컴포넌트)는 구현 시 확정(설계는 IA·데이터 계약까지).

## 3. UI/UX
- **탭**: 오늘자 기사 / 생성 쇼츠 / **설정**.
- **설정 하위**: 종목(체크박스)·키워드·소스 토글·기간 · 시나리오 템플릿(노브 폼) · 배경 자산(업로드·태그).
- **근거**: 시나리오·완성본에 "관계·출처" 패널.
- **홈 지표**: 그래프·기사·이슈·잡 카운트 카드.

## 4. Logic
- content `ui_router`에 `/ui/settings/{tab}`(GET/PUT) — admin API 프록시. `/ui/jobs/{id}/evidence`(관계·출처). 홈 `/ui`에 `QualityMetrics`(research·content 조회).
- static 화면 개편(탭·설정 폼·근거 패널·지표 카드).

## 5. File Map
- `[Mod] services/content/app/domains/content/ui_router.py` — 설정 프록시·근거·지표 라우트
- `[Mod] services/content/app/static/index.html` — 탭·설정·근거·지표 UI
- `[Mod] services/content/app/domains/content/service.py`·`repository.py` — 지표 집계
- `[New] doc/design/content/api-contract-dashboard-redesign.py`

## 6. Verification
- 탭 전환·설정 왕복(admin 반영)·근거 표시·지표. 기존 생성 흐름 회귀. mypy·계약.

## 7. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260726 | /builder(P2) | **㊵ P2 프런트**(index.html 개편, P1 라우트 소비). 설정 탭(maintab 3번째) + 서브탭 6종 폼: 종목(체크·검색)·키워드(추가/삭제/토글)·소스(토글)·기간(select)·시나리오 템플릿(노브 편집·추가·삭제)·배경 자산(등록·삭제·토글). 품질 지표 스트립(`#metrics` 5카드, `loadMetrics`). 근거 패널(`renderEvidence` — 시나리오 편집·완성본 미리보기에 관계·출처·수치). CSS(metrics·subtabs·setrow·evi) 추가. **검증**: JS 구문 `node --check` OK, div 103/103·script 1/1 균형, 재빌드 후 FE 셸 요소 존재(settings 탭·metrics·렌더러), FE 호출 경로 라이브 200(설정 조회·키워드 왕복·period `/_`·템플릿 PUT·배경 POST/DELETE). **범위/한계**: DOM 시각 렌더는 브라우저 수동 확인(헤드리스 미검증) — 셸 서빙·JS 구문·라우트 데이터로 대체 검증. 배경은 메타(경로) 등록 — 파일 업로드(멀티파트)는 후속. |
| 20260725 | /builder(P1) | **㊵ P1 백엔드 라우트**(사용자 결정: 백엔드 먼저, 프런트 P2). content ui_router: `/ui/metrics`(품질지표)·`/ui/jobs/{id}/evidence`(근거)·`/ui/settings/{tab}` GET/POST/PUT/DELETE(admin 프록시). `dashboard.py`(신규): `gather_metrics`(그래프·기사·이슈·완성잡, 각 실패 0)·`build_evidence`(관계·출처·수치, chart 슬롯 치환·순수함수). `admin_client.admin_request`(제네릭 HMAC 중계). `research_client.fetch_graph_stats`. config `issue_detector_url`. research: `neo4j_repo.graph_stats`(노드·관계 count)·`GET /research/graph/stats`·schema. schemas: MetricsRes·EvidenceRes·GraphStatsResponse. **검증**: 단위 content 2(evidence)·회귀 research 13, mypy strict 0(content 6·research 3), 계약 0. 실스택(재빌드 research·content): graph stats 12531/13907·`/ui/metrics`(이슈10·완성잡32)·설정 조회(stocks47·templates3·sources·period)·키워드 왕복(POST→admin_db→DELETE)·evidence job49(관계2·출처8·수치 치환). **범위**: 탭·폼·패널·카드 프런트(AC1 및 AC2~4 UI)는 P2. **이탈**: 근거 수치 표시가 `{close}` 미치환이라 data_slots로 사실값 치환 추가(AC3 정확도). |
| 20260725 | /design | M2 대시보드 리디자인. 탭(오늘자·쇼츠·설정) + 설정(admin ㉝·㊳·㊴ 중계) + 근거(관계·출처) 뷰 + 품질 지표. content가 admin API east-west 중계(Database per Service). 마법사 유지. 무인증 로컬(ADR 0010, M4에서 게이트웨이 뒤로). 계약 mypy 통과. |
