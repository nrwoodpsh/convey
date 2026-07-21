# 20260721 — 요약: market-feed pykrx 실시세 연동

- **Task**: `doc/design/research/task-research-20260720.md` (라운드①, ADR 0008)
- **작업**: /run(builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 KRX·실 Kafka)
- **상태**: market-feed가 mock을 벗고 **키 없는 실 KRX 시세**를 발행. e2e 검증 완료.

## 개요

market-feed의 mock(임의 가격) 시세 소스를 **pykrx**(무료·인증키 불필요)로 교체했다. KRX 일봉 최신 거래일을 실측해 `market.ticks`로 발행하고, 실 KRX·실 Kafka로 관통을 검증했다. ADR 0008(KIS 제외·pykrx 채택)의 시세 축을 실구현으로 완료했다.

## 변경사항 (BE)

- `services/market-feed/app/external_client.py` — `ExternalMarketClient`(mock/KIS) → **`KrxMarketClient`**. `latest_ohlcv(ticker, today)`가 `lookback_days` 창을 조회해 마지막 거래일 OHLCV를 실측 반환(데이터 없으면 None → 스킵). 부패방지 계층(한글 컬럼·DataFrame → 내부 tick 딕트).
- `services/market-feed/app/worker.py` — `KrxMarketClient` 사용. pykrx 동기 호출을 `asyncio.to_thread`로 감싸 이벤트 루프 비차단. 발행 tick에 OHLCV+`source="KRX"`. 폴링 60s로 완만(일봉).
- `services/market-feed/app/config.py` — KIS 필드(`external_base_url`·`kis_app_key`·`kis_app_secret`) 제거, `lookback_days=30` 추가.

## API/계약 변경

- `doc/design/research/api-contract.py` `MarketTickEvent`: **`open`·`high`·`low` 추가**(PriceTick OHLCV 채움), 기본 `source` `"KIS"`→`"KRX"`. contract-gate(mypy --strict) 통과.

## DB

- 변경 없음(발행 계층만). `market.ticks` → `PriceTick` 저장 소비자는 별도 라운드.

## 검증 (전부 실서비스·로컬)

- **실 KRX**: 005930/000660/035420 최신 거래일 OHLCV 실측(삼성전자 close 248,000 등, 키 없이).
- **실 Kafka e2e**(localhost:29092): KRX 실측 tick → `market.ticks` produce → consume, payload 동일(ticker·close·volume·source 일치).
- mypy --strict clean(3파일), contract-gate clean.
- 참고: pykrx가 "KRX 로그인 실패" 경고를 찍으나 이는 로그인 필요한 *다른* 기능용 메시지이며 OHLCV 조회는 키 없이 정상.

## 특이사항 (남은 작업·후속)

- **이탈**: mock KIS → pykrx(ADR 0008 실행), 계약에 OHLC 추가·source 기본값 변경. task History에 기록.
- **남음(후속)**: research가 `market.ticks`를 소비해 `PriceTick` 저장(별도 라운드). 거시(ECOS/FRED)·공시(DART)는 무료 키 발급 후.
- 커밋: 아직(사람 게이트 — `/commit`).
