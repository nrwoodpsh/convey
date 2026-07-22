# 20260722 — 요약: 운영 대시보드 (content, 첫 프론트엔드)

- **Task**: `doc/design/content/20260722-task-dashboard.md` (라운드㉒)
- **작업**: /run(builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료. CONVEY 첫 브라우저 화면 — 생성 버튼·최신순 목록·mp4 미리보기. 실 스택 전 AC 통과.

## 개요

CONVEY는 API 전용 BE였다(화면 = 쇼츠 영상뿐). 운영자가 브라우저에서 **① 생성 버튼 → 제작 시작 · ② 결과 제목·미리보기 · ③ 이전 것까지 목록**을 하도록, content 서비스가 정적 대시보드 + 무인증 운영 API(`/ui/*`) + mp4 스트리밍을 **호스트 포트 8091**에 노출한다. gateway·Supabase 인증 우회(로컬 운영 콘솔, ADR 0010). 기존 `/content/*`(gateway·HMAC)와 발행 사람승인 가드레일은 불변.

## 변경사항

- **BE(content)**:
  - `[New] ui_router.py` — 무인증 라우터: `GET /`(셸)·`POST /ui/generate`(start_generation 재사용, owner_id="dashboard")·`GET /ui/jobs`·`GET /ui/jobs/{id}`·`GET /ui/contents/{id}/video`(FileResponse, content_id로 경로확인→경로주입 방지, Range 자동).
  - `[Mod] repository.py` — `list_jobs`(최신순·limit clamp)·`get_content`.
  - `[Mod] schemas.py` — `DashboardGenerateReq`·`JobListItem`·`JobListRes`.
  - `[Mod] main.py` — `include_router(ui_router)`.
- **FE**: `[New] static/index.html` — 바닐라 단일 파일. 사이버 테마(다크+네온 청록/마젠타, 발광 보더·모서리 클립·주사선), 생성 폼·상태 네온 배지·2.5s 폴링·9:16 `<video>` 미리보기. 외부 CDN 없음(자기완결).
- **설정**: `[Mod] docker-compose.yml` — content `ports: ["${DASHBOARD_PORT:-8091}:8000"]`.
- **문서**: `[New] ADR 0010`(로컬 대시보드·gateway 우회) · `[Mod] operations.md`(8091 접속 안내).

## API 변경 (계약 `api-contract-dashboard.py`)

- 신규(무인증, content 호스트 포트): `GET /` · `POST /ui/generate` · `GET /ui/jobs` · `GET /ui/jobs/{job_id}` · `GET /ui/contents/{content_id}/video`.
- 에러: `CNT004`(404, 완성본 mp4 없음) 신설.
- 기존 `/content/*`(gateway·HMAC)·JobStatus·JobRes 불변(재사용).

## 검증 (실 컨테이너 스택 — localhost:8091)

- AC1 `POST /ui/generate` → job#19 생성 → `scripting`(제작 실제 시작), 목록 최상단.
- AC2 `GET /ui/jobs` 최신순(19→18→…).
- AC3 mp4 `HTTP 200 video/mp4 13.7MB` + **Range `206` content-range/accept-ranges** + 없는 id→CNT004(404).
- AC4 `GET /` 200(자기완결 HTML). AC5 API 전 구간 실 스택 왕복.

## 피드백 반영 (같은 라운드 2차 — 영상·브랜드)

사용자 피드백으로 아래를 이어서 반영(같은 uncommitted 라운드):

- **단일 종목명 소스**: `[New] libs/common/common/stocks.py` — `STOCK_NAMES`(ticker→한글명)·`stock_name`·`stock_label`("현대차(005380)"). 영상·대시보드·자동양산 공유(사전 밖은 코드 노출, 이름 지어내지 않음).
- **영상(video-assembly)**: `render.py` `ChartOverlay`에 `title`·`stock_label` — **최상단 제목(주제) + 그 아래 '한글명(코드)'**(코드만 표시 X). `worker.py`가 title·stock_label 주입.
- **자동양산 제목(content)**: `consumer.py handle_issue` — 제목을 `stock_name` 우선("현대차 이슈", 코드 X).
- **대시보드(FE)**: 표→**카드 그리드**. **필터 탭(완료·실패·전체, 기본 완료)** — 과거 e2e/테스트/자동 잡 클러터 분리. 종목은 **한글명만**(코드 X). `JobListItem.name`(repository가 `stock_name` 채움) + 계약 반영.
- **브랜드 리스타일**: 초기 "사이버틱" → 사용자 제공 **`Brandlogy_Template.pptx`** 기준으로 전면 교체 — 화이트+미세그리드, 크림슨 `#C1001B`, 맑은 고딕, `brandlogy.` 워드마크(`static/assets/*.png`, `main.py`에 `/assets` StaticFiles 마운트), 마침표 모티프. 테두리 강조 유지(패널 상단 레드 라인·카드 좌측 상태 바·프리뷰 모서리 브래킷).

- **미리보기 시나리오**: `[New] GET /ui/contents/{id}/script`(content→job→Script, 차트 슬롯 사실값 채움 + 출처 URL) + `repository.get_script_by_job` + 계약 `ScriptView`. FE 프리뷰가 비디오 옆에 섹션(훅·차트·사실·거시)+근거를 노출.
- **배경 영상**: `consumer._BROLL_MAP` 대표 산업 키워드 개선(현대차=`car factory assembly line`, 삼성=`microchip circuit macro` 등), **기본값=우주의 불빛**(`galaxy space stars glowing`) — 알려진 종목=산업, 미지=코스믹. ADR 0009 폴백 사슬 유지.

**추가 검증**: 새 영상 job#20/job#21(현대차) 프레임 육안 — "현대차 실적 리뷰" 제목 + **현대차(005380)** + 416,500원·+4.39%·한글 자막, job#21은 공장 배경으로 교체 확인. `/ui/jobs` name=삼성전자/현대차/SK하이닉스. `/ui/contents/14/script` 섹션+출처 반환. `/`·워드마크 자산 200.

## 특이사항 (설계 대비·후속)

- **이탈1(TDD)**: `list_jobs`/`get_content` TDD 계획 → 저장소에 **DB 테스트 하니스 부재**(전 테스트 순수 로직). DB 픽스처 신설 대신 **실 컨테이너 API 검증(AC5)**로 대체(얇은 래퍼·관례 준수·과설계 회피).
- **이탈2(디자인)**: "사이버틱" → 브랜드 템플릿(Brandlogy)로 대체(사용자 지시).
- **후속**: research·news-feed의 종목명 사전(name→ticker)은 `common.stocks`로 통합 미완(중복 잔존) — 별도 라운드. 전체 종목 마스터(pykrx/KRX). 운영 배포 시 8091 비노출/gateway+Supabase 뒤로.
- 커밋: 아직(사람 게이트 — `/commit`). mp4·프레임은 공유 볼륨/스크래치(레포에 없음).
