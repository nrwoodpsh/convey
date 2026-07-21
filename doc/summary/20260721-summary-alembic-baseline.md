# 20260721 — 요약: Alembic 베이스라인 (research·content·publishing)

- **대상**: research·content·publishing DB 스키마 (기존 갭 — 커밋된 마이그레이션 0개, 테이블은 임시 create_all로만 존재)
- **작업**: /builder→sync · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(temp DB로 검증, 실 dev DB 불변)
- **상태**: 세 서비스 베이스라인 마이그레이션 신설 + 빈 DB에서 스키마 생성 검증. `price_ticks` 멱등을 DB 제약으로 승격.

## 개요

지금까지 Postgres 테이블은 검증 중 `Base.metadata.create_all`로 임시 생성됐고, 재현 가능한 배포 경로(커밋된 마이그레이션)가 없었다. 이를 메꾸려고 **Alembic 베이스라인**을 각 서비스에 만들었다. autogenerate로 현재 모델을 반영하고, **빈 임시 DB에 `upgrade head`로 스키마가 실제 생성되는지** 검증했다. 실 dev DB는 건드리지 않았다(적용은 사람이 — 가드레일).

## 변경사항

**스캐폴딩 보강**
- `services/research/alembic/script.py.mako`·`services/content/alembic/script.py.mako` (신규) — 마이그레이션 템플릿 부재로 autogenerate 불가였던 것 해소.
- `services/publishing/{alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/}` (신규) — publishing엔 alembic 자체가 없었음. `pyproject.toml`에 `alembic` 의존성 추가.

**베이스라인 마이그레이션 (신규)**
- research `60c1465028e2` — `articles`, `price_ticks`(+ **`uq_price_ticks_ticker_ts` UNIQUE(ticker, ts)**, 인덱스 2)
- content `aa3ccec70626` — `generation_jobs`, `scripts`(JSON), `contents`(+ job_id 인덱스)
- publishing `ba3a7f7a1796` — `publish_records`(content_id UNIQUE 멱등 인덱스)

**모델**
- `services/research/app/domains/research/models.py` — `PriceTick.__table_args__`에 `UniqueConstraint("ticker","ts")` 추가. 앱 레벨 멱등(upsert)을 **DB 제약으로 승격**(직전 라운드 후속 정리).

## DB

- 검증은 임시 DB(`research_mig`·`content_mig`·`publishing_mig`)에서 수행 후 drop. **실 dev DB 불변.**
- 실 dev DB 적용은 운영자 단계(ONBOARDING에 절차 추가): 신규 환경은 `alembic upgrade head`, 이미 create_all로 테이블이 있는 dev DB는 `alembic stamp head`(단 research_db `price_ticks` UNIQUE는 없으면 별도 추가).

## 검증 (실 Postgres, temp DB)

- `alembic upgrade head` → 빈 DB에 테이블 전부 생성 확인:
  - research_mig: articles·price_ticks(**UNIQUE CONSTRAINT uq_price_ticks_ticker_ts** btree(ticker,ts) 확인)·alembic_version=60c1465028e2
  - content_mig: generation_jobs·scripts·contents·alembic_version=aa3ccec70626
  - publishing_mig: publish_records·alembic_version=ba3a7f7a1796
- 모델 mypy --strict clean, 마이그레이션 파일 문법 OK.

## 특이사항 (남은 작업·후속)

- **sample-domain**은 이미 `0001_init` 보유 — 변경 없음.
- 서비스는 시작 시 create_all을 하지 않는다(마이그레이션이 스키마 정본). e2e 드라이버의 create_all은 검증 편의용.
- **후속**: compose에 마이그레이션 실행 단계(초기화 잡) 추가 검토, 실 dev DB에 베이스라인 stamp 적용(사람).
- 커밋: 아직(사람 게이트 — `/commit`).
