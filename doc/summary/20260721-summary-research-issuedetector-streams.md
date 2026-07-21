# 20260721 — 요약: market.ticks→PriceTick 저장 + issue-detector 실 스트림 e2e

- **Task**: `doc/design/research/task-research-20260720.md`(라운드①) · `doc/design/issue-detector/task-issue-detector-20260720.md`(라운드②)
- **작업**: /run(builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 KRX·실 RSS·실 Kafka·실 PG)
- **상태**: 시세 사실 레이어(PriceTick) 완성 + 이슈 랭킹 실 스트림 관통 검증. 둘 다 실서비스 통과.

## 개요

두 가지를 마쳤다. **#1** research가 `market.ticks`(pykrx 실시세)를 소비해 `PriceTick`(사실)으로 **멱등 저장**하도록 소비자를 신설했다. **#2** issue-detector가 실 KRX 시세 + 실 RSS 뉴스 스트림을 소비해 이슈 랭킹을 내는 것을 실 Kafka로 관통 검증했다(코드 변경 없음 — 기존 배선의 e2e 확인).

## 변경사항 (BE)

**#1 — research market.ticks 소비자 (신규 코드)**
- `services/research/app/domains/research/repository.py` — `upsert_price_tick`: 같은 `(ticker, ts)`면 OHLCV 갱신, 없으면 삽입(멱등). market-feed가 같은 일봉을 반복 발행하므로 중복 방지.
- `services/research/app/consumer.py` — `handle_tick`(이벤트→PriceTick 저장) + `run_tick_consumer`(Kafka 루프, group `research-ticks`). 시세는 그래프/LLM 미경유(사실만).
- `services/research/app/config.py` — `topic_ticks="market.ticks"` 추가.
- `services/research/app/main.py` — `run_tick_consumer` 백그라운드 태스크 등록.

**#2 — issue-detector 실 스트림 e2e (코드 변경 없음)**
- 기존 `worker.run_consumers`(두 토픽 소비) + `RollingRanker` + `GET /issues/today`가 실 스트림에서 동작함을 검증만.

## API/계약 변경

- 없음(이번 라운드). `MarketTickEvent`의 OHLC 확장은 직전 pykrx 커밋에서 반영됨.

## DB

- `research_db.price_ticks`에 실 KRX tick 저장(멱등). 스키마 변경 없음.
- 멱등은 **애플리케이션 레벨**(SELECT→update/insert). `(ticker, ts)` unique 제약·Alembic 베이스라인은 후속(현재 alembic versions 없음 — 기존 갭).

## 검증 (전부 실서비스·로컬)

- **#1 실 KRX→실 research_db**: 005930 실측 tick `handle_tick` 저장(created) → 같은 `(ticker, ts)`·close만 변경 재발행 → 같은 행 갱신(created=False), 행 수 1 유지·close 반영. mypy --strict clean(4파일).
- **#2 실 Kafka e2e**: 실 KRX ticks 3종목 + 실 RSS 뉴스(연합·한경, 035420 자동태깅) 발행 → issue-detector worker가 새 그룹으로 소비(earliest, ticks 4·news 7) → 랭킹 산출.
  - 랭킹(24h): ①005930 score 1.610(등락 +2.62%·vol_z 1.0) ②035420 0.400(news 2) ③000660 0.
  - **윈도우 필터 정확성**: 005930 뉴스가 24h 창 밖이라 news=0, 720h 창에선 news=1 — `published_at` 기준 필터가 실제로 동작.

## 특이사항 (남은 작업·후속)

- issue-detector는 설계상 **DB 미접속**(스트림만 소비, 경계 유지) — 재기동 시 랭킹 상태 재구축. 실 데이터로 정상 동작 확인.
- **후속**: `price_ticks` `(ticker, ts)` unique + Alembic 베이스라인(멱등을 DB 제약으로 승격), 거시(ECOS/FRED)·공시(DART) 무료 키 발급 후 수집, content/agent가 PriceTick·Article을 근거로 스크립트·렌더.
- 커밋: 아직(사람 게이트 — `/commit`).
