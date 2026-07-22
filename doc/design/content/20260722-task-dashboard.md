# 20260722-task-dashboard.md

> 라운드 ㉒ (운영 대시보드 — 첫 프론트엔드). ADR 0010. 계약: `api-contract-dashboard.py`.
> CONVEY 첫 화면(브라우저). 로컬 전용·무인증. 유튜브 업로드는 사람이 수동.

## 1. Requirements

- **결론**: 운영자가 브라우저에서 **① 생성 버튼 → 쇼츠 제작 시작 · ② 결과(제목·미리보기) 확인 · ③ 이전 것까지 차곡차곡 목록**을 하도록, content 서비스가 정적 대시보드 + 운영 API(`/ui/*`) + mp4 스트리밍을 **새 호스트 포트**(8091)에 노출한다.
- **서빙/인증**(ADR 0010): `/ui/*`·`/`는 **gateway·Supabase 인증 없이** content 호스트 포트로 직접. 기존 `/content/*`(gateway·HMAC)는 불변. 로컬 운영 콘솔.
- **Acceptance Criteria**:
  - [x] AC1: `POST /ui/generate {topic, ticker?}` → 잡 생성(`start_generation`, owner_id="dashboard") → `{job_id}` 반환. 버튼 클릭으로 제작이 실제 시작된다(status pending→…). **검증: job#19 → scripting.**
  - [x] AC2: `GET /ui/jobs` → 최신순(created_at desc) 목록 `[{job_id, topic, ticker, status, content_id, created_at}]`. 이전에 만든 것이 차곡차곡 보인다.
  - [x] AC3: `GET /ui/contents/{content_id}/video` → 완성 mp4 스트리밍(Range 지원) → 대시보드 `<video>`로 재생. 없으면 CNT004(404). **검증: 200 video/mp4 + Range 206 + 999999→404.**
  - [x] AC4: `GET /` → 정적 대시보드(index.html): 생성 폼(제목·종목) + 목록(상태 배지·시간) + 선택 시 미리보기. 상태는 폴링으로 갱신. **검증: 200, 자기완결.**
  - [x] AC5: 실 브라우저로 생성→완료→재생 1회 왕복 확인(실 컨테이너 스택, localhost:8091). **검증: API 전 구간 실 스택.**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **인증 우회 범위**: `/ui/*`만 무인증. 기존 `/content/*`는 `gateway_user`(HMAC) 유지 — 새 라우터에 의존성을 **붙이지 않도록** 분리(실수로 붙이면 브라우저 401). 반대로 `/content/*`에서 떼면 안 됨(east-west 보안).
  - **mp4 스트리밍**: Content.mp4_path = 컨테이너 내부 경로(`/data/media/job-{id}.mp4`, 공유 볼륨). content 컨테이너가 그 볼륨을 마운트하므로 FileResponse로 그 경로를 직접 서빙. FileResponse는 Range를 지원(브라우저 시킹). **경로 신뢰**: content_id로 DB 조회 후 파일 서빙(경로 주입 방지 — 사용자 입력 경로 금지).
  - **호스트 포트 충돌**: gateway 8080·PG 5432·Neo4j 7474/7687·Kafka 29092·kafka-ui 8090 사용 중. content 대시보드는 **8091** 신규(8090 kafka-ui와 1 차이 주의 — 8091 비어있음 확인).
  - **CORS**: 대시보드(정적)와 API가 **같은 오리진**(둘 다 content:8091)이라 CORS 불필요. 별도 오리진으로 가면 필요.
  - **폴링 부하**: 상태 폴링 2~3초 간격, 진행 중 잡만. 완료(ready/approved/failed)면 폴링 중단.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 서빙/인증**: 택함 = **content 직접 서빙(8091, 무인증, gateway 우회)** / 기각 = gateway 경유(Supabase 로그인 UI·프로젝트 선구축 필요, 로컬 과함)·별도 nginx(컨테이너 +1 이점 적음) / 사유 = 로컬 POC·최소 인프라. ADR 0010.
  - **결정 2 — FE 형태**: 택함 = **바닐라 단일 index.html + JS**(프레임워크·빌드 없음) / 기각 = React/Vue(빌드 체인·의존성) / 사유 = POC·얇게. content가 정적 1파일 서빙.
  - **결정 3 — 라우터 분리**: 택함 = **새 `ui_router`(prefix `/ui`, `gateway_user` 미부착)** + 정적 `/` / 기각 = 기존 content_router에 무인증 엔드포인트 혼재(보안 경계 흐림) / 사유 = 인증 경계 명확히(무인증은 /ui에만).
  - **결정 4 — 재생 대상**: 택함 = `content_id` 기반 `/ui/contents/{id}/video`(DB로 경로 확인 후 서빙) / 기각 = job_id·파일명 직접(경로 주입 위험) / 사유 = 경로 신뢰·계약 명확.

## 3. UI/UX (대시보드 = 첫 브라우저 화면)

```
┌──────────────── CONVEY 대시보드 (localhost:8091) ─────────────────┐
│  ▛ 새 쇼츠 만들기                                                  │
│    제목 [ 현대차 실적 이슈           ]  종목 [ 005380 ]  [ 생성 ▶ ] │
│                                                                    │
│  ▛ 내 쇼츠 (최신순)                                                │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ #18  현대차 이슈        005380  [ready]   07-22 14:30   ▶ 재생 ││
│  │ #16  네이버 이슈        035420  [ready]   07-22 13:10   ▶ 재생 ││
│  │ #15  삼성전자 이슈      005930  [assembling] 07-22 …    (진행)  ││
│  │ #14  카카오 이슈        035720  [failed]  07-22 …       (오류)  ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ▛ 미리보기 (#18 현대차 이슈)                                      │
│    ┌─────────────┐  9:16 <video controls> ← /ui/contents/{id}/video│
│    │  쇼츠 재생   │                                                 │
│    └─────────────┘                                                 │
└────────────────────────────────────────────────────────────────────┘
```
- **상태 배지**: pending·scripting·assembling(진행, 폴링) / ready·approved(완료, 재생) / failed(오류, error 표시).
- **폴링**: 진행 중 잡이 있으면 2~3초마다 `GET /ui/jobs` 갱신, 모두 완료면 중단.
- **재생**: ready/approved(content_id 있음) 행의 "재생" → 미리보기 `<video>` src = `/ui/contents/{content_id}/video`.
- 로그인 없음(로컬). 유튜브 업로드 버튼 없음(수동, C 연기).
- **비주얼(확정 — 브랜드 템플릿 `Brandlogy_Template.pptx`)**: **화이트 + 미세 그리드 배경 · 크림슨 레드 `#C1001B`(브랜드 마크에서 추출) · 클린 산세리프(맑은 고딕) · 마침표(`.`) 모티프**. `brandlogy.` 워드마크 로고를 헤더에 노출(static/assets). **테두리 강조**(요구): 패널 상단 레드 라인 + 카드 좌측 상태 컬러 바 + 라운드 보더 + 프리뷰 모서리 브래킷. (초기 "사이버틱" 지시 → 브랜드 템플릿 제공으로 대체.) 종목은 **한글명만**(코드 X), 카드마다 제목·종목명·상태·시각.

## 4. Logic

- **라우터**(`services/content/app/domains/content/ui_router.py` 신규 — 무인증):
  - `GET /` → `FileResponse(static/index.html)`.
  - `POST /ui/generate` → `DashboardGenerateReq` → `service.start_generation(session, producer, GenerateRequest(topic, ticker), owner_id="dashboard")` → `{job_id}`.
  - `GET /ui/jobs?limit=50` → `repository.list_jobs` → `JobListRes`(최신순).
  - `GET /ui/jobs/{job_id}` → `service.get_job` 재사용(`JobRes`).
  - `GET /ui/contents/{content_id}/video` → `repository.get_content` → 없으면 CNT004(404) → `FileResponse(content.mp4_path, media_type="video/mp4")`(Range 자동).
- **저장소 추가**(`repository.py`):
  - `list_jobs(session, limit)` → `select(GenerationJob).order_by(created_at.desc()).limit(limit)` → JobListItem 매핑(created_at은 isoformat).
  - `get_content(session, content_id)` → `session.get(Content, content_id)`.
- **main.py**: `app.include_router(ui_router)` 추가(gateway_user 미부착). 정적 파일 위치 `services/content/app/static/`.
- **에러**: `AppError("CNT004", "완성본(mp4)을 찾을 수 없습니다.", status=404)` 신설(mp4 없거나 파일 부재).
- **owner_id**: 대시보드 생성은 `"dashboard"`(자동양산 `"auto"`, gateway 경유 사용자 id와 구분).

## 5. Implementation Split (다음 /builder)

- **BE(content)**: `ui_router.py`(신규, 무인증) + `repository.list_jobs`·`get_content` + `main.py` include + CNT004. 계약 스키마(`schemas.py`)에 `DashboardGenerateReq`·`JobListItem`·`JobListRes` 추가.
- **FE(content/static)**: `index.html`(바닐라 — 폼·목록·폴링·`<video>`). 단일 파일.
- **인프라**: `docker-compose.yml` content에 `ports: ["8091:8000"]`(mp4 공유 볼륨은 이미 있음).

## 6. File Map (기계적)

- `[New] services/content/app/domains/content/ui_router.py` — 무인증 대시보드 라우터(/·/ui/*)
- `[New] services/content/app/static/index.html` — 바닐라 대시보드 FE
- `[Mod] services/content/app/domains/content/repository.py` — `list_jobs`·`get_content`
- `[Mod] services/content/app/domains/content/schemas.py` — `DashboardGenerateReq`·`JobListItem`·`JobListRes`
- `[Mod] services/content/app/main.py` — `include_router(ui_router)` + 정적 마운트
- `[Mod] docker-compose.yml` — content 호스트 포트 `8091:8000`
- `[Mod] doc/ref/operations.md` — 대시보드 접속(localhost:8091) 안내 추가

## 7. Verification (다음 /builder)

- `list_jobs` 최신순·limit 단위 테스트(GenerationJob N건 → desc 정렬·개수) — TDD.
- `get_content` 없음 → CNT004(404) 단위 테스트.
- `POST /ui/generate` → 잡 pending 생성 + content.generate 발행(기존 start_generation 경유) 검증.
- **실 컨테이너 재생성**(AC5): localhost:8091 접속 → 생성 폼 제출 → 목록에 신규 잡 → 완료 후 `<video>` 재생(Range 200/206). mypy --strict·ruff clean.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 운영 대시보드(첫 FE) — content 직접 서빙(8091, 무인증, gateway 우회, ADR 0010). `/ui/generate`·`/ui/jobs`·`/ui/contents/{id}/video` + 정적 index.html(바닐라). start_generation 재사용, 발행은 사람 승인 불변. 계약 `api-contract-dashboard.py`(mypy 통과). 유튜브 업로드는 수동(C 연기). |
| 20260722 | /builder | 구현·검증 완료(실 컨테이너 스택). `ui_router.py`(무인증)·`repository.list_jobs`/`get_content`·`schemas`(Dashboard\*)·`main.py` include·compose 포트 `8091:8000`·`static/index.html`. **AC 전부 통과**: AC1 `POST /ui/generate`→job#19 scripting(제작 시작), AC2 `/ui/jobs` 최신순, AC3 mp4 200+**Range 206**·CNT004(404), AC4 `/` 200, AC5 localhost:8091 실 왕복. **이탈(Deviation)**: 계획=`list_jobs`/`get_content` TDD. 실제=저장소에 **DB 테스트 하니스 부재**(전 테스트가 순수 로직). 택함=DB 픽스처 신설 대신 **실 컨테이너 API 검증(AC5)**로 대체(관례 준수·얇은 SQLAlchemy 래퍼). 사유=신규 DB 하니스는 이 라운드 범위 밖·과설계. |
| 20260722 | /builder(피드백 2차) | 추가 피드백 2건: ⑤**미리보기에 시나리오 노출** — `GET /ui/contents/{id}/script`(content→job→Script, 차트 슬롯 사실값 채움 + 출처) 신설, FE 프리뷰에 섹션(훅·차트·사실·거시)+근거 URL 렌더. ⑥**배경 영상** — `_BROLL_MAP` 대표 산업 키워드 개선(현대차=car factory assembly line 등), 기본값=**우주의 불빛**(galaxy space stars glowing). **검증**: `/ui/contents/14/script` 섹션+출처 반환; broll 매핑(005380→산업, 미지→코스믹); 새 영상 job#21 프레임 육안 — 공장 배경으로 교체됨(제목·한글명(코드)·수치·자막 정상). 계약에 `ScriptView`·`UI_SCRIPT_ENDPOINT` 추가(mypy OK). |
| 20260722 | /builder(피드백 반영) | 사용자 피드백 4건: ①영상 제목·종목이 코드 → **제목(주제) + 종목 '한글명(코드)'**(render.py `ChartOverlay.title`/`stock_label`, worker), ②대시보드 **카드 그리드**로, ③종목 **한글명만** 표시(schemas/repository `name` + 계약), ④목록에 과거 e2e/테스트/자동 잡 섞임 → **필터 탭(완료·실패·전체, 기본 완료)**. + 자동양산 제목 한글명화(consumer). **단일 종목명 소스** `libs/common/common/stocks.py`(ticker→한글명, `stock_label`) 신설 — 영상·대시보드·자동 공유. **디자인 이탈**: 초기 "사이버틱" → 사용자가 **브랜드 템플릿 `Brandlogy_Template.pptx`** 제공 → 화이트+미세그리드·크림슨 `#C1001B`·맑은 고딕·`brandlogy.` 워드마크(static/assets, `/assets` 마운트)·마침표 모티프로 **전면 리스타일**. **검증(실 스택)**: 새 영상 job#20(현대차) 프레임 육안 — 제목 "현대차 실적 리뷰" + **현대차(005380)** + 416,500원·+4.39%·한글 자막; `/ui/jobs` name=삼성전자/현대차/SK하이닉스; `/` 200·워드마크 자산 200. 후속: 운영 배포 시 8091 비노출/게이트웨이 뒤로, 전체 종목 마스터(pykrx). |
