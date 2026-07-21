# task-macro-search-20260721.md

> 라운드 ⑦ (거시 근거 회수·연결). 알파1(근거·정확). ADR 0008.
> 계약 정본 = `doc/design/research/api-contract.py`(MacroHit·SearchRes.macros 추가). 자연어 설계만.

## 1. Requirements

- **결론**: 라운드⑥에서 거시(ECOS·FRED)를 `MacroIndicator`로 **저장까지** 했으나 `/research/search`가 안 돌려줘서 agent가 못 쓴다. 저장→**회수→스크립트**로 연결해 "금리·환율 맥락이 인용된 쇼츠"까지 닿게 한다.
- **Scenario**: agent가 `GET /research/search` 호출 시 응답에 **최신 거시지표(각 name별 1건, 출처 동반)**가 포함된다. agent가 이를 `build_script`에 넘겨 스크립트에 **거시 맥락 문장 + 인용**을 넣는다.
- **Objective**: 거시 사실을 근거로 노출(무출처 0), 값은 저장된 그대로(조작 0). 종목 무관 전역 맥락.
- **Acceptance Criteria**:
  - [ ] AC1: 계약(`SearchRes.macros`·`MacroHit`) contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: `GET /research/search` 응답 `macros`에 **각 name별 최신 1건**이 `source_url` 동반 포함(실 research_db)
  - [ ] AC3: 회수 거시 값이 저장된 `MacroIndicator`와 **1:1**(조작 0), 무출처 0건
  - [ ] AC4: agent `POST /agent/script` 결과에 거시 맥락이 **citation(source_url) 동반**해 포함(스크립트가 거시 근거 인용)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - "각 name별 최신"을 SQL로 뽑을 때 Postgres `DISTINCT ON (name)` + `ORDER BY name, as_of DESC` 필요(GROUP BY로는 다른 컬럼 못 가져옴).
  - `build_script`는 라운드③ 코드 + 단위테스트가 있다 — 시그니처 바꾸면 **회귀**. `macros`는 **기본값 빈 리스트**로 추가해 기존 호출 불변.
  - 거시는 종목 무관이라 `ticker`/`entity` 없어도 회수돼야 함(검색어와 독립).
  - agent `Retriever.gather`·`ScriptRes` 확장 필요(macros 전달).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 응답 형태**: 택함 = **`SearchRes.macros: list[MacroHit]` 별도 필드** / 기각 = `FactHit`에 `kind='macro'` 흡수 / 사유 = 거시는 종목 무관 전역 맥락이라 facts(종목 사실)와 성격이 다름. 소비 측 분기 단순.
  - **결정 2 — 선택 기준**: 택함 = **각 name별 최신 1건 전량**(소량, POC) / 기각 = 검색어·종목 연관 필터 / 사유 = 거시는 맥락이라 전량이 자연스럽고, 연관 필터는 신호가 약함(후속).
  - **결정 3 — 스크립트 연결 스코프**: 택함 = **이번 라운드에 포함** — `Retriever.gather`가 macros 회수, `build_script(..., macros=[])`가 거시 맥락 섹션·citations 추가 / 기각 = /search 노출까지만 / 사유 = 노출만 하면 파이프라인 끝(스크립트)까지 가치가 안 닿음(라운드⑥의 반복 실수 회피).
  - **결정 4 — build_script 하위호환**: 택함 = `macros` 파라미터 **기본값 `[]`** / 기각 = 필수 인자 / 사유 = 라운드③ 단위테스트·기존 호출 불변(회귀 0).

## 3. UI/UX

해당 없음 (API 전용 BE).

## 4. Logic

**research `/search`**
```
service.search(...):
  facts, relations, price = (기존)
  macros = repository.latest_macros(session, limit)   # DISTINCT ON(name) 최신
  macros = [m for m in macros if m.source_url]         # 가드레일: 무출처 제거
  return SearchRes(..., macros=[MacroHit(...)])
```
- `repository.latest_macros`: `SELECT DISTINCT ON (name) id,name,value,unit,as_of,source,source_url FROM macro_indicators ORDER BY name, as_of DESC LIMIT n`. 값은 저장 그대로(조작 0).

**agent**
```
Retriever.gather(...):
  data = GET /research/search
  macros = [MacroEvidence(name,value,unit,source_url,ref_id) for m in data.macros if source_url]
  return Evidence(price, series, facts, macros)

POST /agent/script:
  script = build_script(topic, price, facts, llm, macros=ev.macros)
```
- `build_script(..., macros: list[MacroEvidence] = [])`:
  - 거시 맥락 섹션 1개 추가(kind='macro'): "기준금리 {v}{unit}, 원달러 {v}원 …" — **수치는 macro 슬롯에서만**(환각 차단, 가격과 동일 원칙).
  - 각 macro → `Citation(claim, source_url, ref_id)` 추가.
  - macros 비면 섹션·인용 없음(기존과 동일).

## 5. Implementation Split (다음 /builder)

- **BE(research)**: `repository.latest_macros` 신설. `schemas.py`에 `MacroHit`. `service.search`가 macros 조립. (router 변경 없음 — 응답 스키마만 확장)
- **BE(agent)**: `retriever.py` `Evidence.macros` + gather 파싱. `script/builder.py` `build_script`에 `macros` 파라미터 + 거시 섹션·citations. `main.py` `/agent/script`가 macros 전달 + `ScriptRes`/`ChartOut` 변경 없음(citations에 흡수).
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] doc/design/research/api-contract.py` — `MacroHit`·`SearchRes.macros` (완료·mypy 통과)
- `[Mod] services/research/app/domains/research/repository.py` — `latest_macros`
- `[Mod] services/research/app/domains/research/schemas.py` — `MacroHit` + `SearchResponse.macros`
- `[Mod] services/research/app/domains/research/service.py` — macros 조립(무출처 제거)
- `[Mod] services/agent/app/rag/retriever.py` — `Evidence.macros` + gather 파싱
- `[Mod] services/agent/app/script/builder.py` — `build_script(macros=[])` 거시 섹션·citations, `MacroEvidence` TypedDict
- `[Mod] services/agent/app/main.py` — `/agent/script`가 macros 전달

## 7. Verification (다음 /builder)

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(실 research_db·실 서비스):
  - `latest_macros` → 각 name 1건, 값 == 저장값(AC3), 모두 source_url(AC2·AC3)
  - `build_script(..., macros=[…])` 단위: 거시 섹션 수치는 슬롯에서만, 모든 macro citation에 source_url(AC4). macros=[] 시 기존과 동일(회귀 0).
  - (전 스택) `/agent/script` 응답 citations에 거시 출처 포함(AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | 거시 회수·연결 설계 — `SearchRes.macros`(각 name 최신) + agent/`build_script` 거시 섹션·citations. 계약에 `MacroHit` 추가. build_script는 `macros=[]` 기본값(회귀 0). |
| 20260721 | /builder | research `latest_macros`(DISTINCT ON name)·`MacroHit` 스키마·`service.search` macros 조립. agent `Retriever.gather` macros 파싱·`build_script(macros=[])` 거시 섹션+citations(`MacroEvidence`)·main 전달. **실 research_db 검증**: `/search.macros` 5종 각 name 최신·출처 동반·값 1:1(AC2·AC3), `build_script` 거시 섹션+5 citations 출처 동반·수치 사실 슬롯만(AC4). mypy·contract-gate clean, builder 단위 3 회귀 없음. 정정: 슬롯 값·단위 사이 공백(가독성). |
