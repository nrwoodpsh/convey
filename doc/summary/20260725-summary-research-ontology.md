# 20260725 — 요약: 지식 그래프 온톨로지 확장 (라운드㉟, ㉞ 흡수)

- **Task**: `doc/design/research/20260725-task-ontology.md` · 계약 `api-contract-ontology.py` · ADR 0018
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: 완료·검증. LLM의 새 형식 준수는 재백필로 관측(후속).

## 개요

POC 최소 온톨로지(5노드·5엣지)를 서비스급으로 확장 — 협력·계열·수혜/타격·인수·제품·테마·정책 표현 + §4에서 발견한 엣지 오용(HAS_EVENT→섹터) 차단. **노드 9·엣지 12 + 사건 속성(event_type·direction) + 엣지 domain/range 제약**. ㉞(엔티티 타입검증)을 흡수.

## 변경사항 (BE)

- **`extract/relations.py`**:
  - `EDGE_TYPES` 5→**12**(PARTNERS_WITH·AFFILIATE_OF·BENEFITS_FROM·HURT_BY·PRODUCES·ACQUIRES·REGULATES 추가). `ENTITY_TYPES` 5→**9**(제품·테마·정책·국가). `ENTITY_STOPWORDS` 보강(노조·노사·이동통신사 등).
  - `EDGE_DOMAIN_RANGE`(엣지별 양끝 타입)·`EVENT_TYPES`·`TypedEntity`(name·type·event_type·direction).
  - `build_graph_prompt`: `{name,type,event_type?,direction?}` + 12엣지 요구. `_parse_graph`: 객체/문자열 하위호환.
  - `extract_graph`: 엔티티 타입 검증(허용 밖 폐기) + `_edge_ok`(domain/range 위반 폐기). `Graph`에 `types`·`events` 필드.
- **`graph/neo4j_repo.py`**: `upsert_entity`가 `type`·`event_type`·`direction`을 있을 때만 SET(하위호환 옵션). `upsert_relation` 화이트리스트는 12엣지(EDGE_TYPES 재사용).
- **`consumer.py`·`backfill.py`**: `upsert_entity`에 타입·사건 속성 전달.

## API/타입 변경

- `extract_graph` 시그니처·반환 골격 유지(Graph에 기본값 필드 추가). `upsert_entity`에 선택 파라미터 추가(하위호환). Kafka 이벤트 불변. 계약 `api-contract-ontology.py`.

## 검증

- 단위 **13/13**(`test_relations.py`): ㉚·㉛ 회귀 + ㉟(HAS_EVENT→섹터 폐기·BELONGS_TO→섹터 채택·PARTNERS_WITH 확장·event_type/direction 파싱·타입 허용밖 폐기).
- mypy `--strict` 0(4파일). 
- **실스택**(재빌드): 어휘 12/9/13 반영 확인·타입 노드 속성(type/event_type/direction) 저장 라이브 확인(테스트 노드 정리).

## 특이사항 (설계 대비·후속)

- **하위호환**: 레거시 문자열 엔티티·타입 미상은 기존 경로(domain/range는 타입 알 때만 검사) → ㉚·㉛ 불변.
- **LLM 준수는 별개**: qwen이 새 `{name,type}` 형식을 실제 얼마나 지키는지는 **재백필로 관측**(우리 코드 로직은 결정론 단위테스트로 증명).
- **기존 5어휘 데이터**와 혼재 — 신규부터 확장, 재백필은 후속. 노드 타입 라벨(:기업 등)은 속성으로 두고 라벨화는 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
