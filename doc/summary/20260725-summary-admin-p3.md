# 20260725 — 요약: news-feed ↔ admin config 연동 (라운드㉝ P3)

- **Task**: `doc/design/admin/20260724-task-admin-collection.md` (P3) · 계약 `api-contract-admin.py` · ADR 0016
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: P3 완료·검증. admin P1(설정 저장) → news-feed(수집)까지 배선 작동.

## 개요

admin P1이 저장한 운영자 설정(종목·키워드·소스)을 news-feed가 **API로 읽어 수집에 반영**한다(㉝ P3). 하드코딩 `TICKER_DICT`/전-소스 대신, `GET /admin/config`의 활성 종목·키워드로 검색어를 만들고 소스 토글을 적용. admin 불가 시 하드코딩 폴백(견고성).

## 변경사항 (BE)

- **`services/news-feed/app/admin_client.py`**(신규):
  - `fetch_config()` — `GET /admin/config`를 east-west(HMAC `sign_internal`)로 조회. 실패 시 None.
  - `derive_queries(config)` — 활성 종목명 + 키워드(중복·공백 제거) → 검색어.
  - `source_enabled(config, name)` — 소스 토글(미설정 기본 ON).
- **`services/news-feed/app/worker.py`**: `_news_loop`가 매 사이클 admin config로 검색어·소스 결정(`_maybe`로 소스별 조건 수집), 실패 시 하드코딩 폴백. `_maybe` 헬퍼 추가.
- **`services/news-feed/app/config.py`**: `admin_url` 추가.

## API 변경

- news-feed → admin `GET /admin/config` 소비(east-west HMAC). Kafka 이벤트·계약 불변.

## 검증

- 단위 **13/13**: `derive_queries`(종목+키워드·중복제거)·`source_enabled`(기본 ON·토글) + tagging 회귀 10.
- mypy `--strict` 0(3파일).
- **실스택**(재빌드): news-feed가 admin config 라이브 조회 → 검색어 **47개(하드코딩 아닌 admin_db 종목)** · 소스 토글 · 기간 1w. Database per Service(API만).

## 특이사항 (설계 대비·후속)

- **폴백**: admin 불가 시 하드코딩 종목·전 소스 ON — 견고성.
- **범위/후속**: 광역 RSS(사회·정치 피드 확대)는 `feed_urls` 설정이라 P3 범위 밖(admin 관리로 이관 가능). P3 핵심 = 검색어·소스 토글의 admin 구동.
- **남은 admin 라운드**: P2(대시보드 설정 UI)·P4(issue-detector 연동).
- 커밋: 아직(사람 게이트 — `/commit`).
