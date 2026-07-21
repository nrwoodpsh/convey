# task-source-expansion-20260721.md

> 라운드 ⑥ (소스 확장 — 받은 무료 키 실연동). 알파1(근거·정확). ADR 0008.
> 계약 정본 = `doc/design/research/api-contract.py`(MacroIndicatorEvent 추가). 자연어 설계만.

## 1. Requirements

- **결론**: 지금 뉴스는 RSS(무작위)뿐이고, 공시·거시는 키가 없어 꺼져 있었다. 방금 받은 무료 키(Naver 뉴스검색·DART·ECOS·FRED)로 **근거 소스를 4배로 넓힌다**. 종목 타깃 뉴스·실적 공시·금리/환율/물가까지 사실로 축적한다.
- **Scenario**: `news-feed`가 (a) RSS + (b) **Naver 뉴스검색**(종목명으로) + (c) **DART 공시**를 `research.ingested`로, (d) **ECOS·FRED 거시 지표**를 `research.macro`로 발행한다. `research`가 소비해 Article·Event(그래프) + **MacroIndicator**(사실)로 저장한다.
- **Objective**: 모든 수집물이 **출처·라이선스 메타 동반**(무출처 0 — 알파1). 거시는 그래프 미경유 사실(Postgres). 무료 소스만.
- **Acceptance Criteria**:
  - [ ] AC1: 계약(`api-contract.py`) contract-gate(`mypy --strict`) 통과 — ✅ (MacroIndicatorEvent 추가됨)
  - [ ] AC2: **Naver 뉴스검색** 실키로 종목 타깃 뉴스가 `source_url`(원문 링크) 동반해 `research.ingested` 발행 → research 저장
  - [ ] AC3: **DART** 실키로 공시 수집 → `Article`(출처=DART 링크) 저장
  - [ ] AC4: **ECOS·FRED** 실키로 `MacroIndicator` 저장, **저장값이 API 응답과 1:1 일치**(값 조작 0)
  - [ ] AC5: 모든 수집물이 출처·라이선스 메타 동반 — **무출처 0건**(가드레일)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대(부딪히면 배울 함정)**:
  - `research`엔 **MacroIndicator ORM·소비자가 없다** — 신규 모델 + `research.macro` 소비 핸들러 + Alembic 마이그레이션(베이스라인 `60c1465028e2` 다음) 필요.
  - Naver 검색 `description`은 **HTML 태그(`<b>`)·엔티티(`&quot;`)** 포함 — 정제 필요. `originallink`가 비는 경우 `link`(네이버 경유) 대체.
  - ECOS/FRED는 **지표마다 통계표코드·series_id가 다르다** — 코드를 config로 빼서 하드코딩 피함. ECOS 응답은 문자열 값(`DATA_VALUE`) → float 변환.
  - 거시는 **저빈도**(일/월) — 뉴스 폴링(5분)과 같은 주기로 돌리면 낭비·중복. 별도 주기·멱등 필요.
  - Naver 검색 무료 한도(25,000/일) — 종목 수 × 주기 곱이 한도 안인지.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 거시 수집 소유**: 택함 = **`news-feed`에 거시 폴링 루프 추가**(별도 async 태스크·별도 주기) / 기각 = 신규 `macro-feed` 서비스 / 사유 = POC에서 서비스 하나 더 = compose·배포 부담. news-feed는 이미 "외부 수집 워커". *(ADR 0008이 "news-feed 확장 또는 신규" 열어둠 → 확장 채택)*
  - **결정 2 — 거시 전달 경로**: 택함 = **신규 토픽 `research.macro`** + research 신규 핸들러 → `MacroIndicator` 저장 / 기각 = `research.ingested`에 type 필드 섞기 / 사유 = 거시는 Article이 아니라 사실(그래프·LLM 미경유), 섞으면 소비 분기 복잡.
  - **결정 3 — Naver 검색 쿼리**: 택함 = **`TICKER_DICT`의 종목명으로 종목별 검색**(종목 타깃 — 알파1 직결) / 기각 = 일반 키워드 검색 / 사유 = RSS가 이미 무작위 커버, Naver는 타깃 보강이 가치. 검색으로 이미 종목 아니 `tickers` 사전 태깅 확실.
  - **결정 4 — 거시 지표 집합**: 택함 = **config로 지표 목록(코드) 관리**, POC 기본 = ECOS(기준금리·원달러환율·CPI) + FRED(연방기금금리·미 CPI) / 기각 = 코드 하드코딩 / 사유 = 지표는 늘 바뀜, 코드는 설정.
  - **결정 5 — 멱등**: 택함 = MacroIndicator `(name, as_of, source)` 유니크 upsert(가격 tick과 동일 패턴) / 기각 = 매번 insert / 사유 = 저빈도 반복 폴링 → 중복 방지.
  - **결정 6 — 가격 출처 정정**: 택함 = `PriceEvidence.source_url`을 **KRX 정보데이터시스템**(`data.krx.co.kr`, pykrx 원천)으로 / 기각 = 네이버 파이낸스 유지 / 사유 = 데이터 실제 출처는 KRX. 표기 정확성(알파1).

## 3. UI/UX

해당 없음 (API 전용 BE, 수집 워커).

## 4. Logic

**news-feed (수집·발행)**
```
[뉴스·공시 루프 — 기존 주기]
  RSS.fetch() + Naver.search(각 종목명) + DART.fetch_recent()
    → 각 doc {title, body(정제), source_url, license, published_at}
    → 규칙 태깅(tickers·entities·event_hints)
    → research.ingested 발행
[거시 루프 — 별도 주기(일 1회)]
  ECOS.fetch(지표코드들) + FRED.fetch(series들)
    → MacroIndicatorEvent {name, value, unit, as_of, source, source_url}
    → research.macro 발행
```
- Naver: `openapi.naver.com/v1/search/news.json?query={종목명}` (헤더 `X-Naver-Client-Id/Secret`). `title`/`description`에서 HTML 태그·엔티티 제거. `source_url`=`originallink`(없으면 `link`), `license`="NAVER".
- DART: 기존 `DartClient.fetch_recent`(키 있으면 동작). `source_url`=DART 공시 링크, `license`="DART".
- ECOS: `ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/1/{표코드}/{주기}/{시작}/{끝}` → 최신 `DATA_VALUE`(str→float). `source`="ECOS", `source_url`=ECOS 통계 페이지.
- FRED: `api.stlouisfed.org/fred/series/observations?series_id=&api_key=&file_type=json&sort_order=desc&limit=1` → 최신 `value`. `source`="FRED", `source_url`=FRED series 페이지.

**research (저장)**
```
research.ingested → handle_ingested (기존: Article + 관계추출 + 그래프)
research.macro   → handle_macro (신규): MacroIndicator upsert (name,as_of,source 멱등)
```
- 가드레일: `source_url` 빈 값이면 저장 안 함(무출처 0). 거시 값은 API 실측 그대로(조작 0 — AC4).

## 5. Implementation Split (다음 /builder 대상 — 이번 라운드는 설계만)

- **BE(news-feed)**: `NaverNewsClient`(부패방지 계층) 신설, worker에 Naver 병합. `EcosClient`·`FredClient` 신설 + 거시 폴링 루프(별도 태스크·주기). config에 키·지표코드·주기.
- **BE(research)**: `MacroIndicator` ORM + `handle_macro` 소비자 + `run_macro_consumer` 배선(main). Alembic 마이그레이션(macro_indicators, 베이스라인 다음).
- **BE(research)**: `repository.price_source_url` → KRX로 정정.
- **문서/설정**: `.env.example`에 `NAVER_CLIENT_ID/SECRET`·`ECOS_API_KEY`·`FRED_API_KEY` 자리, `KIS_*` 제거. `doc/ref/external-credentials.md`에 4소스 발급·확인 절차.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] doc/design/research/api-contract.py` — `MacroIndicatorEvent`·`TOPIC_RESEARCH_MACRO` 추가 (완료·mypy 통과)
- `[New] services/news-feed/app/external_client.py`에 `NaverNewsClient`·`EcosClient`·`FredClient` 추가(또는 분리 모듈)
- `[Mod] services/news-feed/app/worker.py` — Naver 병합 + 거시 폴링 루프
- `[Mod] services/news-feed/app/config.py` — `naver_client_id/secret`·`ecos_api_key`·`fred_api_key`·지표코드·`macro_poll_interval`
- `[Mod] services/research/app/domains/research/models.py` — `MacroIndicator`
- `[New] services/research/alembic/versions/{rev}_macro_indicators.py` — 마이그레이션(베이스라인 다음)
- `[Mod] services/research/app/consumer.py` — `handle_macro`·`run_macro_consumer`
- `[Mod] services/research/app/config.py`·`main.py` — `topic_macro` + 백그라운드 소비자
- `[Mod] services/research/app/domains/research/repository.py` — `price_source_url` KRX 정정 (+ 후속: MacroIndicator 조회)
- `[Mod] .env.example` — NAVER·ECOS·FRED 자리, KIS 제거
- `[Mod] doc/ref/external-credentials.md` — 4소스 발급·확인 절차

## 7. Verification (다음 /builder)

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(실키·실서비스·로컬):
  - Naver: "삼성전자" 검색 → 뉴스 items(originallink 동반) → `research.ingested` → research_db Article (AC2·AC5)
  - DART: 실키 `fetch_recent` → 공시 Article(출처=DART 링크) (AC3·AC5)
  - ECOS/FRED: 실키 조회값 == 저장 `MacroIndicator.value`(1:1) (AC4), 모든 행 `source_url` 존재 (AC5)
  - 무출처 항목 저장 0건 확인

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | 소스 확장 설계 — Naver 뉴스검색·DART·ECOS·FRED 실연동. 거시=news-feed 확장+`research.macro`→MacroIndicator(사실). 계약에 MacroIndicatorEvent 추가. 가격 출처 KRX 정정. 무료 소스만. |
| 20260721 | /builder | news-feed에 `NaverNewsClient`·`EcosClient`·`FredClient` 신설 + worker 2루프(뉴스/거시). research에 `MacroIndicator` 모델·`handle_macro`·`run_macro_consumer` + Alembic `2dea57e84dfe`(베이스라인 다음). 가격 출처 KRX 정정. `.env.example`(NAVER/ECOS/FRED, KIS 제거)·`external-credentials.md` 정비. **실키·실 research_db 검증**: ECOS·FRED 5종 **API값==DB값 1:1**+멱등(AC4), Naver→Article(license NAVER, AC2), DART→Article(삼성전자 공시, AC3), 무출처 0(AC5). mypy·contract-gate clean, 태깅 단위 6 회귀 없음. **이탈**: ECOS 주기별 날짜포맷(D/M/Y)·최신관측 로직 버그 발견→수정(초기 8자리 고정·오래된 행 반환). |
