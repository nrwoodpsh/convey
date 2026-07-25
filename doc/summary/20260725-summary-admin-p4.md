# 20260725 — 요약: issue-detector ↔ admin 관심목록 게이팅 (라운드㉝ P4)

- **Task**: `doc/design/admin/20260724-task-admin-collection.md` (P4, AC5) · 계약 `api-contract-admin.py` · ADR 0016
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: P4 완료·검증. admin 관리 프로그램 P1~P4 전 구간(설정 저장 → 수집 → 이슈 선별) 배선 완료.

## 개요

운영자가 admin에 등록한 관심 종목만 이슈로 발행하도록 게이팅(㉝ P4, AC5). issue-detector의 `run_emitter`가 매 발행 주기마다 `GET /admin/config`를 읽어 활성 종목 티커 집합(watchlist)을 만들고, 랭킹 상위라도 **관심 밖 종목이면 issue.selected 발행에서 제외**한다. admin 조회 실패 시 게이팅 없음(전량 발행) — 견고성 폴백.

## 변경사항 (BE)

- **`services/issue-detector/app/admin_client.py`**(신규):
  - `fetch_config()` — `GET /admin/config`를 east-west(HMAC `sign_internal`)로 조회. 실패(연결·비200) 시 None.
  - `watchlist_tickers(config)` — config.stocks(활성만 담김)에서 티커 집합 도출.
- **`services/issue-detector/app/worker.py`**: `run_emitter`가 매 주기 `asyncio.to_thread(fetch_config)`로 관심목록 조회 → `watch is not None and r.ticker not in watch`면 `continue`(제외). None이면 게이팅 없음.
- **`services/issue-detector/app/config.py`**: `admin_url` 추가.
- **`services/issue-detector/pyproject.toml`**: `httpx>=0.27` 추가 — 순수 워커라 HTTP 의존이 없었음(east-west 호출용 신규).

## API 변경

- issue-detector → admin `GET /admin/config` 소비(east-west HMAC). Kafka 이벤트(issue.selected)·계약 불변.

## 검증

- 단위 **7/7**: `watchlist_tickers`(티커 집합·빈 config) 2 + ranking 회귀 5.
- mypy `--strict` 0(3파일).
- **실스택**(재빌드): issue-detector가 admin config 라이브 조회 → 활성 **47종목**, 게이팅 정상(005930 삼성전자 in / 미등록 999999 out). Database per Service(admin_db 직접접근 없이 API만).

## 특이사항 (설계 대비·후속)

- **폴백**: admin 불가 시 watch=None → 게이팅 없음(전량 발행). 견고성 우선.
- **이탈**: issue-detector에 `httpx` 신규 의존(east-west 호출). 최초 재빌드 시 `ModuleNotFoundError: httpx`로 드러나 pyproject에 추가 후 재빌드.
- **관심 = 종목 티커 집합**: 설계의 "코스피200 ∪ 키워드" 중 P4는 종목 티커 게이팅으로 구현. 키워드 기반 확장(뉴스 매칭 종목 추가)은 후속 여지.
- **admin 프로그램 완료**: P1(서비스·DB·시드·API) → P2(대시보드 UI, 후속) → P3(news-feed 수집) → P4(issue-detector 게이팅). P2(설정 UI)는 M2 대시보드 리디자인 라운드에서 진행.
- 커밋: 아직(사람 게이트 — `/commit`).
