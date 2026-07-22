# 20260722 — 요약: 대시보드 v2 (탭·마법사·템플릿·배경)

- **Task**: `doc/design/content/20260722-task-dashboard-v2.md` (라운드㉔)
- **작업**: /run(builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료. 대시보드를 탭 2개 + 마법사 5단계로 재배치, 시나리오 템플릿·수정·배경 선택 추가. 실 스택 검증.

## 개요

대시보드 배치·흐름 재설계: 상단 **탭 2개**(`오늘자 기사`=제작 마법사 / `생성쇼츠`=완료 목록·미리보기). 마법사 **① 기사 → ② 템플릿 → ③ 시나리오 수정 → ④ 배경·생성 → ⑤ 미리보기**. 시나리오 템플릿 3종(구성·톤), 사람이 시나리오 텍스트 편집, 배경 실사/애니 선택, 출처 표시 제거, 기사는 당일만.

## 변경사항

- **agent(BE)**: `ScriptReq.template`(breaking|analysis|story) + `build_script(template)` — `_TEMPLATES`로 사용 사실 수·거시 포함·마무리(closing)·훅 문체 분기. 기본 analysis(기존 동작=회귀0).
- **content(BE)**:
  - `_call_agent_script(template)`·`handle_generate` 템플릿 전달·`start_generation(template)`.
  - `service.update_script`(scenario_ready만 텍스트 갱신, 차트 수치 고정)·`approve_scenario(background)`.
  - `media.broll_query(ticker, background)` — anim=`abstract motion graphics loop`, real=종목 산업(미지=우주의 불빛). `build_assemble_event(background)`.
  - `ui_router`: `PUT /ui/jobs/{id}/script`(수정)·`approve-scenario` 바디 `background`·`/ui/generate` 템플릿·`/ui/articles` 당일 고정(7일 폴백 제거).
  - 스키마: `DashboardGenerateReq(+template)`·`ScriptEditReq`·`ApproveScenarioReq`.
- **FE**: `static/index.html` 재작성 — 탭 2개, 마법사 5단계(스텝 진행바), 템플릿·배경 선택 칩, 섹션 편집 textarea, 출처 렌더 제거. 다크(검정+레드+금색) 유지.

## API 변경 (계약 `api-contract-dashboard.py`)

- 신규: `PUT /ui/jobs/{job_id}/script`(시나리오 수정).
- 변경: `POST /ui/generate`에 `template` · `POST /ui/jobs/{id}/approve-scenario`에 `background`.
- 상수: `SCENARIO_TEMPLATES`(breaking·analysis·story) · `BACKGROUND_KINDS`(real·anim). agent `ScriptReq.template`.
- 마이그레이션 없음(background는 approve 바디).

## 검증 (실 컨테이너 스택 — localhost:8091)

- AC2/5 템플릿: 속보형 job#24 = `[hook, chart, fact]`(거시 없음) — 분석형(사실3+거시)과 구성 다름.
- AC3 수정: `PUT /ui/jobs/24/script`(200) → hook "[수정됨] 삼성전자 오늘의 핵심 이슈" 반영. 출처 UI 없음.
- AC4 배경: `approve{background:anim}` → ready(content 18) → broll = 추상 스파이럴 모션그래픽(실사 job과 대비).
- AC6 end-to-end: 영상 프레임 — 삼성전자(005930)·260,500원·+2.36·**편집 자막 반영**·애니 배경.

## 특이사항 (설계 대비·후속)

- **이탈**: 배경은 approve 바디 전달(새 컬럼 회피) · TDD DB 하니스 부재로 실 스택 검증 · 템플릿 기본 analysis=기존 동작(자동양산 회귀0).
- 시나리오 chart 텍스트 "260500.0원" 소수점 표기(영상 렌더는 260,500원) — 후속.
- 후속: LLM 훅이 따옴표로 감싸는 경우 있음(정리) · research·news-feed 종목명 사전 `common.stocks` 통합 · 운영 배포 시 8091 비노출.
- 커밋: 아직(사람 게이트 — `/commit`).