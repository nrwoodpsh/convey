# 20260722 — 요약: 대시보드 재설계 (기사→시나리오→승인→생성)

- **Task**: `doc/design/content/20260722-task-dashboard-workflow.md` (라운드㉓)
- **작업**: /run(builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료. 대시보드를 근거(기사) 기반 승인 워크플로우로 재편. 다크 테마. 실 스택 전 흐름 검증.

## 개요

대시보드를 **오늘자 수집 기사 목록 → 선택 → 진행(초안) → 시나리오 제시 → 승인 → 쇼츠 생성**으로 재편했다(ADR 0011). 근거 없는 생성 차단(알파1), 영상 만들기 전 사람이 시나리오 승인. 자동양산(알파4)은 승인 없이 무정지 유지. 테마는 검정+레드+금색, brandlogy 제거, 미리보기 상단.

## 변경사항

- **research(BE)**: `GET /research/articles`(window_days·limit, 최신순) + `repository.list_articles` + `service.list_articles`(대표 ticker·한글명) + `ArticleItem`/`ArticleListResponse`.
- **content(BE)**:
  - `[New] research_client.py` — research east-west(HMAC)로 기사 회수.
  - `[New] media.py` — 내레이션·broll·assemble 이벤트 공용 헬퍼(consumer/service 공유, 순환 import 방지).
  - `[Mod] ui_router.py` — `/ui/articles`·`/ui/jobs/{id}/script`·`POST /ui/jobs/{id}/approve-scenario`, `/ui/generate` 기사기반(auto=False).
  - `[Mod] service.py` — `start_generation(auto)`·`approve_scenario`(scenario_ready만 → media.assemble → assembling).
  - `[Mod] consumer.py` — `handle_generate` auto 분기(자동=합성 직행, 수동=chart 보존·scenario_ready 정지), `handle_issue(auto=True)`.
  - `[Mod] models.py`+`alembic c1d2e3f40011` — `GenerationJob.chart`(JSON, 승인 시 합성 재사용).
  - `[Mod] schemas.py` — `JobStatus.SCENARIO_READY`·`ArticleItem`/`ArticleListRes`·`DashboardGenerateReq`(기사기반).
- **agent(BE)**: `builder.py` chart 문장 `{ticker} 종가…` → `{한글명} 종가…`(공유 `common.stocks`, 코드 제외).
- **FE**: `static/index.html` 재작성 — 다크(검정+레드+금색), 미리보기 상단, 기사 목록→시나리오→승인 흐름, 카드+필터 탭. `static/assets/brandlogy-*` 삭제, `main.py` `/assets` 마운트 제거.

## API 변경 (계약 `api-contract-dashboard.py`)

- 신규: `GET /research/articles`(research) · `GET /ui/articles` · `GET /ui/jobs/{id}/script` · `POST /ui/jobs/{id}/approve-scenario`.
- 변경: `POST /ui/generate` 요청이 기사기반(`title`·`ticker`·`article_id`).
- 상태: `JobStatus`에 `scenario_ready`(수동 승인 대기) 추가. 에러 `CNT003`(승인 불가 상태) 재사용.

## 검증 (실 컨테이너 스택 — localhost:8091)

- AC1 `/ui/articles`: 실 수집 기사 251건 회수(east-west), 현대차·삼성전자 한글명.
- AC2/3/4: job#22 기사선택 → `scripting → scenario_ready`(합성 안 함) → 시나리오 chart **"현대차 종가 416500.0원, 4.39%"(코드 없음)** → `approve-scenario` → `assembling → ready`(content 16) → 재승인 **CNT003(409)**.
- AC6: 영상 프레임 육안 — 제목·현대차(005380)·수치·자막·공장 배경. 다크 대시보드·brandlogy 없음.

## 특이사항 (설계 대비·후속)

- **AC5(자동양산 무정지)**: `auto=True` 분기가 기존 동작 보존 — 코드경로 검증. 신규 run은 dedup(최근 잡)으로 이번엔 미실시.
- **영상 시각 라벨**은 한글명(코드) "현대차(005380)" 유지(㉒ 사용자 요청). **시나리오·내레이션만** 코드 제외.
- 시나리오 chart 텍스트 "416500.0원" 트레일링 .0 — 표시상 소수점(영상 렌더는 416,500원). 후속 다듬기.
- research·news-feed 종목명 사전(name→ticker) `common.stocks` 통합 미완(중복 잔존). 전체 종목 마스터(pykrx). 운영 배포 시 8091 비노출.
- 커밋: 아직(사람 게이트 — `/commit`).