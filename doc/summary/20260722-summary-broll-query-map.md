# 20260722 — 요약: broll 검색어 종목 매핑 (B3)

- **Task**: `doc/design/content/task-broll-query-map-20260722.md` (라운드⑯, 쇼츠 완성도)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 Pexels)
- **상태**: broll 검색어를 종목→영문 섹터 키워드로 매핑. 종목별 다른 배경. 5개 AC 충족.

## 개요

기존 broll 검색어가 `"stock market"` 고정이라 어느 종목이든 같은 배경이었다. ticker→영문 섹터 키워드 매핑으로 종목 맥락에 맞는 배경(반도체·자동차·배터리 등)을 받게 했다. 무키 추가 없음(기존 Pexels 키).

## 변경사항 (BE, content)

- `consumer.py` — `_BROLL_QUERY` 상수 → `_BROLL_MAP`(005930·000660 semiconductor / 035420·035720 internet technology / 005380 automobile factory / 373220 battery factory) + `_broll_query(ticker)`(폴백 "stock market"). `handle_generate`가 ticker로 매핑해 `media.assemble`에 전달.

## API/계약 변경
- 없음. 마이그레이션 없음.

## 검증 (실 Pexels·로컬)

- **AC2**: 005930→semiconductor, 005380→automobile factory, 373220→battery factory 등 종목별 상이.
- **AC3**: 미지 종목(999999)·None → "stock market" 폴백.
- **AC4**: 실 Pexels — semiconductor(컴퓨터 칩)·automobile factory(자동차) **서로 다른 배경** 반환.
- **AC5**: `handle_generate` payload `broll_query`가 매핑값. mypy --strict clean.

## 특이사항 (후속)

- POC 주요 6종목 사전. **전체 KRX 확장·섹터 테이블화**는 후속(news-feed `TICKER_DICT`와 통합 위치 검토).
- 영문 키워드(Pexels 커버리지, 라운드⑫ 교훈).
- 커밋: 아직(사람 게이트 — `/commit`).
