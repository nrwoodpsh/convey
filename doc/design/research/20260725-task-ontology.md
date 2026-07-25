# 20260725-task-ontology.md

> 라운드 ㉟ (지식 그래프 온톨로지 확장 — 서비스급). ADR 0018.
> 계약: `api-contract-ontology.py`. 도메인 research(`extract/relations.py`·`graph/neo4j_repo.py`). 로컬 Ollama만.
> **㉞(엔티티 타입검증 + 엣지-양끝 제약)을 흡수·확장** — 같은 코드라 구현은 한 번에(㉞ 별도 빌드 불필요).

## 1. Requirements

- **문제**: 현 온톨로지(5노드·5엣지)가 최소라 서비스에 부족. 협력(PARTNERS)·계열(AFFILIATE)·수혜/타격(BENEFITS/HURT)·인수(ACQUIRES)·제품·테마·정책·공시유형(유상증자·무상증자·인수 등)·방향(증가/감소)을 못 담음. §4 점검에서 **엣지 오용**(HAS_EVENT→섹터, SUPPLIES→섹터)도 확인.
- **목표**: 서비스급 온톨로지로 확장 — **노드 9·엣지 12 + 사건 속성(event_type·direction) + 엣지 domain/range 제약**(양끝 타입 검증). 이 제약이 §4 엣지 오용을 차단.
- **핵심 모델링 결정**(설계):
  - **공시 유형(유상증자·무상증자·인수 등) = 새 노드/엣지 아님 → 사건(Event)의 `event_type` 속성**(폭발 방지). HAS_EVENT는 그대로.
  - **방향(증가/감소·호재/악재) = 사건의 `direction` 속성**(BENEFITS_FROM/HURT_BY 엣지와 짝).
  - **정량 수치(주문량·가동률·매출액)는 그래프 아님 → Postgres(사실)**. 그래프는 **정성 이벤트·관계만**. (뉴스가 "주문 증가"라 하면 사건+direction으로 담되, 주문 "수치"는 안 모음 — 데이터 소스 한계.)
- **Acceptance Criteria**:
  - [x] AC1: 확장 어휘 — `ENTITY_TYPES` 9종·`EDGE_TYPES` 12종 반영, LLM 프롬프트가 이를 요구. **검증: 상수·프롬프트에 12엣지·9노드 포함, mypy·계약.**
  - [x] AC2: **엣지 domain/range 제약** — 양끝 타입이 `EDGE_DOMAIN_RANGE`에 부합해야 채택. **검증: 스텁이 `HAS_EVENT(기업→섹터)` 반환 → 폐기(목적어=사건이어야). `BELONGS_TO(기업→섹터)` → 채택.**
  - [x] AC3: 사건 속성 — `event_type`(유상증자 등)·`direction`(긍정/부정) 파싱·저장. **검증: 스텁이 `{type:사건,event_type:유상증자,direction:부정}` → 노드 속성에 반영.**
  - [x] AC4: **하위호환·회귀** — 타입/속성 없는 레거시 반환도 기존 경로, ㉚·㉛ 테스트 통과. `extract_graph` 시그니처·반환 골격 유지 → consumer·backfill 무변경. **검증: 기존 단위 통과.**
  - [x] AC5: 가드레일 — 환각컷(substring)·근거 결속·seed 무조건·결정론 엣지(섹터·사건)·로컬 Ollama 불변.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**:
  - **결정 1 — event_type/direction = 속성**(새 타입 아님): 폭발 방지. 유상증자·인수·수주를 사건 속성으로.
  - **결정 2 — 노드 타입 = `:Entity`의 `type` 속성**(신규 라벨 남발 X): `:Stock`만 별도 라벨 유지(시세 연계). 9개 라벨 도입은 후속(질의 필요 시).
  - **결정 3 — ㉞ 흡수**: ㉞의 타입검증 + 엣지-양끝 제약이 ㉟의 부분집합 → **㉞ 별도 빌드 안 함, ㉟로 통합**.
- **사각지대**:
  - **본문 얕음(§2)**: 제품·테마·정책·국가·수주를 발췌 본문에서 LLM이 얼마나 뽑을지 불확실 → 수율 낮을 수 있음. 관측 후 프롬프트·예시 보강. (수집 광역화 ㉝와 시너지.)
  - **LLM 오용↑**: 어휘가 12엣지로 늘어 오분류 위험↑ → **domain/range 제약이 방어선**. 프롬프트에 엣지별 예시 필수.
  - **섹터 vs 테마 중복**: 섹터=산업분류(반도체), 테마=투자모멘텀(AI·저PBR) — 프롬프트로 구분 지시. 겹치면 관측 후 조정.
  - **direction 주관성**: 호재/악재 판단이 LLM 주관 → "중립" 허용, 강한 것만. 수치 독립검증 아님(뉴스 진술).
  - **기존 그래프**: 5어휘로 쌓인 데이터와 12어휘 혼재 → 신규부터 확장, **재백필은 후속**(대량 재추출).
  - **재추출 비용**: 프롬프트·검증 변경 → 백필 재실행 필요(사람). 정량 데이터(주문·수주 수치)는 **별개 데이터 소스 과제**(범위 밖).

## 3. UI/UX
- 화면 변화 없음. 결과: 그래프가 풍부해져 시나리오가 **"왜 올랐나"(수혜/타격·협력·계열)**를 방향까지 말함 → 영상 품질(알파①)↑.

## 4. Logic (`extract/relations.py`·`graph/neo4j_repo.py`)
- 상수: `ENTITY_TYPES`(9)·`EDGE_TYPES`(12)·`EDGE_DOMAIN_RANGE`·`EVENT_TYPES`·`Direction`.
- `build_graph_prompt`: 노드 9·엣지 12·event_type·direction을 **예시와 함께** 요구. 형식 `{"entities":[{name,type,event_type?,direction?}],"relations":[{subject,edge,object}]}`.
- `_parse_graph`: 엔티티를 `TypedEntity`(name·type·event_type·direction), 관계를 `TypedRelation`로. 레거시(문자열) 하위호환.
- `extract_graph`: 엔티티 채택(㉞ 규칙 + type∈ENTITY_TYPES) → 관계 채택에 **domain/range 검증** 추가: `subject_type ∈ dr[edge][0] ∧ object_type ∈ dr[edge][1]`(빈 tuple=무제한). 위반 폐기.
- `neo4j_repo.upsert_entity`: `type`·`event_type`·`direction`을 노드 속성으로 SET. `upsert_relation`: 화이트리스트를 12엣지로.
- `consumer.py`: 결정론 엣지 유지(종목→섹터 BELONGS_TO, event_hints→HAS_EVENT의 event_type).

## 5. Implementation Split
- relations.py(어휘·프롬프트·파싱·domain/range 검증) + neo4j_repo.py(속성·엣지 화이트리스트) + 테스트. consumer·backfill 배선 최소(시그니처 유지). ㉞ 통합.

## 6. File Map (기계적)
- `[Mod] services/research/app/extract/relations.py` — 확장 어휘·domain/range·event_type/direction·프롬프트·파싱·검증
- `[Mod] services/research/app/graph/neo4j_repo.py` — 노드 속성(type·event_type·direction)·엣지 화이트리스트 12
- `[Mod] services/research/app/consumer.py` — 결정론 엣지 event_type 반영(경미)
- `[Mod] services/research/tests/test_relations.py` — 확장 어휘·domain/range 폐기·event 속성·회귀
- `[New] doc/design/research/api-contract-ontology.py` · `[New] doc/decisions/0018-*.md`

## 7. Verification
- 단위(스텁): AC2 domain/range(HAS_EVENT→섹터 폐기, BELONGS_TO→섹터 채택) / AC3 event_type·direction / AC1 어휘 / AC4 회귀(㉚·㉛). 
- 통합(실 스택): 재빌드 + 재백필 표본 — BENEFITS_FROM/HURT_BY·PARTNERS·AFFILIATE 엣지 생성, HAS_EVENT→섹터 오용 소멸 확인.
- 가드레일: 환각 0·근거 결속·로컬 Ollama. mypy·계약 통과.

## 8. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /builder | 구현·검증. `relations.py`: EDGE_TYPES 5→12·ENTITY_TYPES 5→9·`EDGE_DOMAIN_RANGE`·`EVENT_TYPES`·`TypedEntity`·스톱워드 보강. `build_graph_prompt`(타입·event·direction 요구)·`_parse_graph`(객체/문자열 하위호환)·`extract_graph`(타입검증+`_edge_ok` domain/range)·`Graph`(types·events 필드). `neo4j_repo.upsert_entity`(type·event_type·direction 속성 SET, 하위호환 옵션). `consumer.py`·`backfill.py`가 속성 전달. **검증**: 단위 13/13(㉚·㉛ 회귀 + ㉟: HAS_EVENT→섹터 폐기·BELONGS_TO→섹터 채택·PARTNERS 확장·event 파싱·타입 폐기), mypy strict 0(4파일). 실스택(재빌드): 어휘 12/9/13 반영·타입 노드 속성 저장 라이브 확인. **후속**: qwen이 새 {name,type} 형식을 실제로 얼마나 준수하는지는 재백필로 관측(LLM 준수는 별개). |
| 20260725 | /design | 온톨로지 확장(서비스급) — 노드 5→9(제품·테마·정책·국가), 엣지 5→12(PARTNERS·AFFILIATE·BENEFITS/HURT·PRODUCES·ACQUIRES·REGULATES), 사건 속성 event_type(유상증자·인수·수주 등)·direction(호재/악재), **엣지 domain/range 제약**(§4 오용 차단). 결정: 공시유형·방향=속성(폭발방지), 노드타입=속성(라벨남발X), **㉞ 흡수**. 정량수치=Postgres(그래프 아님). 사각지대: 본문 얕아 수율 불확실·LLM 오용↑(제약이 방어)·섹터vs테마·재백필 후속. 계약 mypy 통과. ADR 0018(ADR 0014·0017 확장). |
