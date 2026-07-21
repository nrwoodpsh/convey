# 20260721 — 요약: 소스 확장 (Naver·DART·ECOS·FRED 실연동)

- **Task**: `doc/design/research/task-source-expansion-20260721.md` (라운드⑥, ADR 0008)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실키·실 research_db·실 Kafka 무관 — 클라이언트·저장 직접 검증)
- **상태**: 무료 키 4종(Naver·DART·ECOS·FRED) 실연동 완료. 근거 소스가 RSS 하나에서 넷으로 확장. 5개 AC 충족.

## 개요

받은 무료 키로 근거 소스를 넓혔다. 종목 타깃 뉴스(Naver 검색) + 실적·공시(DART) + 거시 지표(ECOS·FRED)를 수집해, 뉴스·공시는 `Article`(그래프)로, 거시는 `MacroIndicator`(사실)로 저장한다. 모두 출처 동반(알파1). 거시 값은 API와 1:1(조작 0).

## 변경사항 (BE)

**news-feed — 소스 클라이언트 + 워커 2루프**
- `app/external_client.py` — `NaverNewsClient`(종목명 검색, HTML 정제, 출처=originallink) · `EcosClient`(주기별 날짜포맷 D/M/Y, 최신관측) · `FredClient`(series 최신) 신설
- `app/worker.py` — `_news_loop`(RSS+Naver+DART→research.ingested) + `_macro_loop`(ECOS+FRED→research.macro, 저빈도) 동시 실행
- `app/config.py` — NAVER/ECOS/FRED 키 + 지표 집합(기본값, JSON 오버라이드) + macro 주기

**research — 거시 사실 저장**
- `app/domains/research/models.py` — `MacroIndicator`(+ `(name,as_of,source)` UNIQUE)
- `app/domains/research/repository.py` — `upsert_macro`(멱등) + `price_source_url` 네이버→**KRX 정정**
- `app/consumer.py` — `handle_macro` + `run_macro_consumer`
- `app/config.py`·`main.py` — `topic_macro` + 백그라운드 소비자

**계약**
- `doc/design/research/api-contract.py` — `MacroIndicatorEvent`·`TOPIC_RESEARCH_MACRO` 추가(contract-gate 통과)

## DB

- research_db에 `macro_indicators` 테이블 — Alembic `2dea57e84dfe`(베이스라인 `60c1465028e2` 다음). **실 research_db에 upgrade head 적용**(버전=head).

## 검증 (실키·실서비스·로컬)

- 4 클라이언트 실키 호출: Naver(3건, 출처 동반)·DART(삼성전자 공시)·ECOS(기준금리 2.5%·환율 1527.0·CPI 116.52)·FRED(연방기금금리 3.63%·CPI 332.568).
- **AC4**: ECOS·FRED 5종 저장 → **API값 == MacroIndicator.value 1:1**, 멱등 재저장 created=False.
- **AC2/AC3/AC5**: Naver·DART 문서 → `handle_ingested` → Article 저장, source_url 동반(license NAVER/DART), 무출처 0.
- mypy --strict clean, contract-gate clean, news-feed 태깅 단위 6 회귀 없음.

## 특이사항 (이탈·후속)

- **이탈(수정)**: ECOS 초기 구현이 (1) 주기 무관 8자리 날짜 고정 → 월 지표 실패, (2) 페이지 오름차순 첫 100행만 → 오래된 값 반환. 주기별 포맷(D/M/Y)+최근창 조회로 수정.
- 네이버 검색은 종목명 쿼리라도 느슨히 관련된 결과가 섞임(relevance) — RSS보다 타깃이나 완벽하진 않음. 태깅이 최종 필터.
- 가격 출처 표기를 KRX(`data.krx.co.kr`)로 정정 — 데이터 실제 출처 반영(알파1).
- **후속**: 거시 `MacroIndicator`를 `/research/search`·스크립트 맥락에 노출(현재 저장까지), 지표 집합 확장, 실 Kafka 전송 e2e(핸들러는 검증됨).
- 커밋: 아직(사람 게이트 — `/commit`).
