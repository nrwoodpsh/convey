# task-broll-query-map-20260722.md

> 라운드 ⑯ (B3 — broll 검색어 종목/섹터 매핑). 쇼츠 완성도. ADR 0008·0009.
> 계약 변경 없음. 자연어 설계만.

## 1. Requirements

- **결론**: 지금 broll 검색어가 `"stock market"` 고정 → 어느 종목이든 **같은 배경**. 종목/섹터에 맞는 영문 키워드로 매핑해 배경을 다양·적절하게 한다(예: 반도체→semiconductor, 자동차→automobile). 무료(기존 Pexels 키).
- **Scenario**: content가 `media.assemble`에 넣는 `broll_query`를 **ticker 기준 매핑**으로 만든다. 미지 종목은 기본어("stock market").
- **Objective**: 종목 맥락 배경. 무키 추가 없음.
- **Acceptance Criteria**:
  - [ ] AC1: 변경 파일 `mypy --strict` 통과(계약 변경 없음)
  - [ ] AC2: `_broll_query(ticker)`가 **알려진 종목별로 다른 영문 키워드** 반환(예: 005930→반도체 계열, 005380→자동차 계열)
  - [ ] AC3: **미지 종목** → 기본 "stock market" 폴백
  - [ ] AC4: 실 Pexels로 매핑 키워드가 **실제 배경 결과 반환**(검색어별 상이 확인)
  - [ ] AC5: `handle_generate`가 매핑된 `broll_query` 전달, 회귀 없음(수동/자동 동일)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - Pexels는 영문 커버리지가 좋음 → 매핑값은 **영문**(한국어 키워드는 결과 희박, 라운드⑫ 교훈).
  - ticker↔섹터 사전은 news-feed `TICKER_DICT`와 별개 위치(content) — POC 소규모, 중복 최소.
  - 미지 종목 다수 → 폴백 필수.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 매핑 키**: 택함 = **ticker → 영문 키워드 사전**(정확·안정) / 기각 = 종목명 파싱·섹터 추론 / 사유 = ticker가 명확·결정론적.
  - **결정 2 — 위치**: 택함 = **content**(제작 시점 ticker 앎, `_BROLL_QUERY` 상수 대체) / 기각 = video-assembly / 사유 = "무엇을 배경으로"는 content(스크립트/맥락 소유).
  - **결정 3 — 값**: 택함 = **영문 섹터/테마 키워드**(semiconductor·automobile·battery·technology 등) + 폴백 "stock market" / 기각 = 한국어 / 사유 = Pexels 커버리지.
  - **결정 4 — 범위**: 택함 = **POC 주요 종목 사전**(TICKER_DICT 대상), 확장은 후속 / 기각 = 전체 KRX / 사유 = POC 규모.

## 3. UI/UX
해당 없음. 배경이 종목 맥락에 맞게 다양화.

## 4. Logic

```
content:
  _BROLL_MAP = {
    "005930": "semiconductor",  # 삼성전자
    "000660": "semiconductor",  # SK하이닉스
    "035420": "internet technology",  # 네이버
    "035720": "internet technology",  # 카카오
    "005380": "automobile factory",  # 현대차
    "373220": "battery factory",  # LG에너지솔루션
  }
  _broll_query(ticker) = _BROLL_MAP.get(ticker, "stock market")
  handle_generate: media.assemble broll_query = _broll_query(ticker)
```

## 5. Implementation Split (다음 /builder)

- **BE(content)**: `_BROLL_QUERY` 상수 → `_BROLL_MAP` + `_broll_query(ticker)` 함수. `handle_generate`가 ticker로 매핑.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/content/app/consumer.py` — `_BROLL_MAP`·`_broll_query`, handle_generate 적용

## 7. Verification (다음 /builder)

- 계약 변경 없음 → mypy (AC1)
- `_broll_query`: 005930→반도체 계열, 005380→자동차 계열(AC2), 미지→"stock market"(AC3)
- 실 Pexels: 매핑 키워드(semiconductor·automobile)로 검색 → 각각 결과 반환·서로 다른 자산(AC4)
- handle_generate 발행 payload broll_query 확인(AC5)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | broll 검색어 ticker→영문 키워드 매핑(_BROLL_MAP) + 폴백 "stock market". 영문(Pexels 커버리지), content 위치. POC 주요 종목 사전. |
| 20260722 | /builder | `_BROLL_QUERY` 상수 → `_BROLL_MAP`(6종목: 반도체·인터넷·자동차·배터리) + `_broll_query(ticker)`(폴백 "stock market"). handle_generate가 ticker로 매핑 전달. **검증**: 매핑 종목별 상이·미지 폴백(AC2·AC3), **실 Pexels** semiconductor(칩)·automobile(차) 서로 다른 배경(AC4), 발행 payload 반영(AC5). mypy clean. 계약·마이그레이션 없음. |
