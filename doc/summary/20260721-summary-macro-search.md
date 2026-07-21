# 20260721 — 요약: 거시 근거 회수·연결 (MacroIndicator → /search → 스크립트)

- **Task**: `doc/design/research/task-macro-search-20260721.md` (라운드⑦, ADR 0008)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 research_db·실 Neo4j)
- **상태**: 라운드⑥에서 저장만 하던 거시(ECOS·FRED)를 `/research/search`로 회수하고 스크립트에 인용까지 연결. 4개 AC 충족.

## 개요

거시 사실을 파이프라인 끝(스크립트)까지 닿게 했다. `/research/search`가 각 지표 최신 1건을 출처와 함께 반환하고, agent가 이를 `build_script`에 넘겨 **거시 맥락 섹션 + 인용**을 스크립트에 넣는다. "금리·환율 맥락이 인용된 쇼츠"가 가능해졌다.

## 변경사항 (BE)

**research**
- `domains/research/repository.py` — `latest_macros`(DISTINCT ON name, 각 지표 최신 1건, 값 저장 그대로)
- `domains/research/schemas.py` — `MacroHit`(+ ref_id) · `SearchResponse.macros`
- `domains/research/service.py` — `/search` 응답에 macros 조립(무출처 제거 가드레일)

**agent**
- `rag/retriever.py` — `Evidence.macros` + `/search` 응답 macros 파싱(무출처 제외)
- `script/builder.py` — `build_script(..., macros=[])` 거시 맥락 섹션 + citations, `MacroEvidence` TypedDict. 수치는 macro 슬롯에서만(환각 차단)
- `main.py` — `/agent/script`가 `ev.macros` 전달

**계약**
- `doc/design/research/api-contract.py` — `MacroHit` · `SearchRes.macros` 추가(contract-gate 통과)

## API/계약 변경

- `SearchRes`/`SearchResponse`에 `macros: list[MacroHit]` 추가(응답 확장, router·엔드포인트 변경 없음).
- `build_script` 시그니처에 `macros` **선택 파라미터**(기본 `[]`) — 기존 호출·round③ 단위테스트 불변.

## DB

- 변경 없음(회수만). `macro_indicators`는 라운드⑥ 마이그레이션.

## 검증 (실 research_db·실서비스)

- **AC2/AC3**: `service.search('삼성전자', ticker='005930')` → `macros` 5종(기준금리 2.5연%·환율 1527.0원·국내CPI 116.52·연방기금금리 3.63%·미CPI 332.568). 각 name 최신 1건, **저장값과 1:1**, 전부 source_url(무출처 0).
- **AC4**: `build_script(..., macros=…)` → `kind='macro'` 섹션 + 거시 5 citations(출처 동반), 수치는 사실 슬롯만(LLM 거짓숫자 무시). `macros=[]` 시 거시 섹션 없음(회귀 0).
- mypy --strict clean, contract-gate clean, agent builder 단위 3 회귀 없음.

## 특이사항 (후속)

- 거시 선택은 **각 name별 최신 1건 전량**(POC). 종목 연관 필터(어떤 종목엔 어떤 거시가 유의미한지)는 후속.
- 거시 슬롯 표기 값·단위 공백 정정(가독성).
- **후속**: 전 스택 `/agent/script` HTTP 경로에서 거시 citation 포함 재확인(단위·DB 레벨은 검증됨), video-assembly 자막/차트에 거시 맥락 노출 검토.
- 커밋: 아직(사람 게이트 — `/commit`).
