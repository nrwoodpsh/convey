# 20260725 — 요약: admin 서비스 신설 (라운드㉝ P1)

- **Task**: `doc/design/admin/20260724-task-admin-collection.md` (P1) · 계약 `api-contract-admin.py` · ADR 0016
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: P1 완료·검증. P2~P4는 후속.

## 개요

운영자 설정(종목·키워드·소스·기간)과 종목 마스터를 담을 **전용 admin 서비스 + admin_db**를 신설(㉝ P1). 대시보드가 쓰고 워커가 `GET /admin/config`로 읽는다(Database per Service). 종목 마스터를 코드(common.stocks)에서 DB로 승격.

## 변경사항 (신규 서비스 + 인프라)

- **`services/admin/`**(신규): FastAPI + SQLAlchemy + alembic.
  - `domains/admin/models.py`: `stock`(ticker·name·sector·enabled) · `keyword` · `source_toggle` · `collection_settings`.
  - `repository.py`·`service.py`: `build_config`(활성만 조립) + 종목/키워드/소스/기간 CRUD.
  - `router.py`: `GET /admin/config` + CRUD(게이트웨이 HMAC dep). `main.py`·`config.py`·`db.py`.
  - `seed.py`: 종목 시드(멱등 upsert). `alembic/`(init 마이그레이션). `Dockerfile`(migrate→seed→uvicorn).
- **인프라**: `docker-compose.yml` admin 블록 · `infra/db/init` `admin_db` · `gateway/app/config.py` `/admin` 라우트.

## API 변경

- 신규 `GET /admin/config`(워커용 통합 설정) + `/admin/stocks`·`/keywords`·`/sources`·`/settings/period` CRUD. 게이트웨이 `/admin` 라우트. 계약 `api-contract-admin.py`.

## 검증

- 단위 **1/1**(seed `_static_rows` 결정론). mypy `--strict` 0(admin 11파일 + gateway).
- **실스택**(재빌드): admin_db 생성 → 마이그레이션 4테이블 → 시드 **47종목** → `build_config` 라이브(활성 47·소스 3 ON·기간 1w·샘플 정상). `/health` ok.

## 특이사항 (설계 대비·이탈·후속)

- **이탈(시드 규모)**: AC1의 "코스피200(≥150)" 대신 **common.stocks 47(static)**로 시드 — 네이버 200 스크래핑은 별도 큰 작업이라 후속(P1 골격·검증 우선). `seed_source` 스위치는 유지(naver/static/pykrx).
- **기존 postgres 볼륨**엔 init 스크립트 미적용 → 이 세션은 `CREATE DATABASE admin_db` 수동. 신규 배포는 init이 자동 생성.
- **P2~P4 후속**: 대시보드 설정 UI(P2)·news-feed admin 연동(P3)·issue-detector 연동(P4).
- 커밋: 아직(사람 게이트 — `/commit`).
