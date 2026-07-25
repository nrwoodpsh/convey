# 20260725 — 요약: 대시보드 리디자인 백엔드 라우트 (라운드㊵ P1)

- **Task**: `doc/design/content/20260725-task-dashboard-redesign.md` · 계약 `api-contract-dashboard-redesign.py` · ADR 0010
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: AC2·AC3·AC4·AC5 백엔드 완료·검증. AC1 및 UI(폼·패널·카드)는 P2(프런트).

## 개요

M2 대시보드 리디자인의 **데이터 플레인**(백엔드 라우트)을 먼저 구현한다(㊵ P1, 사용자 결정). 프런트 탭·폼이 소비할 API — 설정(admin 중계 CRUD)·근거(관계·출처·수치)·품질 지표 — 를 content에 완비했다. content는 admin_db·research_db·Neo4j를 직접 보지 않고 모두 east-west(HMAC)로 읽는다(Database per Service).

## 변경사항 (BE)

- **content `ui_router.py`**: `/ui/metrics`(품질 지표) · `/ui/jobs/{id}/evidence`(근거) · `/ui/settings/{tab}` GET/POST/PUT/DELETE(admin CRUD 프록시). 기존 라우트·마법사 불변(회귀 없음).
- **content `dashboard.py`**(신규): `gather_metrics(session)`(그래프·오늘 기사·오늘 이슈·완성 잡, 각 원격 실패는 0) · `build_evidence(sections, citations)`(관계=relation 섹션·출처=citation URL 중복제거·수치=chart 섹션 data_slots 치환, 순수 함수).
- **content `admin_client.admin_request`**: admin API 제네릭 HMAC 중계(method·path·json·params → status·body).
- **content `research_client.fetch_graph_stats`**: `GET /research/graph/stats` → (노드, 관계).
- **content `config.issue_detector_url`** 추가. schemas: `MetricsRes`·`EvidenceRes`.
- **research**: `neo4j_repo.graph_stats()`(노드·관계 count, OPTIONAL MATCH) + `GET /research/graph/stats` + `GraphStatsResponse`.

## API 변경

- **content 신규(무인증 /ui, ADR 0010)**: `/ui/metrics`·`/ui/jobs/{id}/evidence`·`/ui/settings/{tab}`(GET/POST/PUT/DELETE).
- **research 신규(east-west HMAC)**: `GET /research/graph/stats`.
- 설정 쓰기는 content가 admin(㉝·㊳·㊴) CRUD로 중계 — admin_db 원천 불변.

## 검증

- 단위: content 2(build_evidence 종류 분리·슬롯 치환·URL 중복제거). 회귀 research 13. mypy `--strict` 0(content 6·research 3), 계약 mypy 0.
- **실스택**(재빌드 research·content):
  - `GET /research/graph/stats` → 노드 12531·관계 13907(백필된 그래프).
  - `GET /ui/metrics` → 그래프 12531/13907·기사 0·이슈 10·완성 잡 32.
  - `GET /ui/settings/*` → stocks 47·templates 3·sources{naver·rss·dart}·period 1w.
  - 설정 왕복: `POST /ui/settings/keywords` → admin_db 반영 확인 → `DELETE`.
  - `GET /ui/jobs/49/evidence` → 관계 2(네이버–토스…)·출처 8(KRX·pressman…)·수치 "네이버 종가 207,500원, 등락률 -5.68%"(슬롯 치환).

## 특이사항 (설계 대비·후속)

- **P2(프런트)**: 탭(오늘자·쇼츠·설정) UI, 설정 폼(종목·키워드·소스·기간·템플릿·배경), 근거 패널, 지표 카드 — index.html 개편. 이번 P1이 그 API를 완비.
- **이탈**: 근거 수치가 `{close}` 슬롯 미치환으로 노출돼, `build_evidence`가 data_slots로 사실값 치환(환각 아님, 저장된 수치) — AC3 정확도 개선.
- **가드레일**: content는 admin_db·research_db·Neo4j 직접접근 없이 API만(Database per Service). /ui 무인증 로컬(ADR 0010, M4에서 게이트웨이 뒤로). 원격 실패는 0·빈 목록(대시보드 관대).
- 커밋: 아직(사람 게이트 — `/commit`).
