# 20260724-task-extract-quality.md

> 라운드 ㉞ (개방형 NER 추출 품질 — 엔티티 타입 검증 + 스톱워드 보강). ADR 0017.
> 계약: `api-contract-extract-quality.py`. 도메인 research(`extract/relations.py`). 로컬 Ollama만.

## 1. Requirements

- **문제(§3/§4 학습에서 실측 발견)**: 개방형 NER이 **일반어를 노드로** 생성 → 관계 오염.
  - §3: `MATCH (n:Entity) WHERE NOT n:Stock` 샘플에 섹터 외 **"노조·노사·이동통신사"** 등장.
  - §4: **"삼성전자 COMPETES 노조/노사/이동통신사"** 관계 확인(근거기사 id는 붙음 = 추적되나 의미 오류).
- **원인(코드 추적)**: ① 프롬프트는 엔티티 타입(기업·인물·사건·기관·섹터)을 요구하나 **`_parse_graph`가 타입을 안 받고 이름만** 취함 → 타입 필터 부재. ② `ENTITY_STOPWORDS`가 **19개뿐** → 노조·노사 등 일반 조직어 통과. 세 관문(substring·len·stopword)을 다 통과.
- **핵심 인식**: 엔티티가 상류, 관계가 하류. **엔티티를 정화하면 관계도 자동 정화**(관계 채택은 `subject/object ∈ 채택 엔티티∪seed`라 기존 로직 그대로).
- **목표**: LLM이 엔티티를 `{name,type}`로 반환 → **허용 타입만 채택**(구조적 근본책) + **스톱워드 보강**(안전망). 환각컷·근거·엣지 5종·로컬 Ollama 불변.
- **Acceptance Criteria**:
  - [ ] AC1: 타입이 허용 밖(예 "일반"·"조직")인 엔티티는 **폐기**. **검증: 스텁 LLM이 `{name:"노조",type:"조직"}` 반환 → 결과 제외.**
  - [ ] AC2: 스톱워드 보강분(노조·노사·이동통신사 등)은 **타입 무관 제외**. **검증: 스텁이 "노조"(타입 무관) → 제외.**
  - [ ] AC3: **하위호환** — LLM이 바레 문자열(레거시) 반환 시 기존 경로(substring+스톱워드)로 처리, ㉚·㉛ 테스트 통과. **검증: 문자열 배열 입력 → 기존대로.**
  - [ ] AC4: **관계 자동 정화** — 폐기된 엔티티가 든 관계는 안 생김. **검증: "노조" 폐기 시 `(삼성전자)-[COMPETES]->(노조)` 미생성.**
  - [ ] AC5: 가드레일 — 환각 0(substring 유지)·근거 결속·엣지 5종·로컬 Ollama만·seed 무조건 신뢰 불변. mypy·계약·기존 테스트 통과.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**:
  - **결정 1 — 근본책**: 택함 = **엔티티 타입 검증**(LLM이 이미 타입을 요구받음 → 받아서 허용 타입만) / 기각 = 스톱워드 확대만(두더지잡기·끝없음) / 사유 = 구조적. 스톱워드는 **보조 안전망**으로 병행.
  - **결정 2 — 하위호환**: 택함 = 바레 문자열도 허용(type 미상→기존 규칙) / 사유 = LLM이 형식 안 지킬 때 전량 유실 방지. ㉚·㉛ 테스트 불변.
- **사각지대**:
  - **노조가 "기관"으로 분류되면 타입필터 통과** — 노조를 LLM이 기관으로 볼 수 있음 → 타입필터만으론 못 잡음. **그래서 스톱워드 보강이 필수 병행**(알려진 노이즈는 확실히 컷).
  - **타입 오분류**: LLM이 실제 기업을 "일반"으로 잘못 줘 유실 가능 → 과도한 폐기 위험. 관측 후 허용 타입·프롬프트 조정. seed는 타입 무관 신뢰라 종목은 안전.
  - **프롬프트 형식 변경**: 출력 형식 바뀌면 기존 파싱 취약 → `_parse_graph` 관대 파싱 유지(객체·문자열 모두).
  - **기존 오염 데이터**: 이미 그래프에 든 노조 노드·관계는 이번 범위 밖(신규부터 정화). 정리는 재백필 후속.
  - **㉜와 구분**: ㉜=news-feed 사전 종목 태깅(카카오톡), ㉞=research 개방형 NER 일반어(노조). 다른 층·다른 파일.

## 3. UI/UX
- 화면 변화 없음(백엔드 추출 품질). 결과: 그래프 노드·관계 정확도↑ → 시나리오·회수 품질 개선(간접).

## 4. Logic (`extract/relations.py`)
- `build_graph_prompt`: 출력 형식을 `{"entities":[{"name","type"}],"relations":[...]}`로. "타입은 기업·인물·사건·기관·섹터 중 하나."
- `_parse_graph`: entities를 `{name,type}` 객체로 파싱(`TypedEntity`). 바레 문자열이면 `type=None`(하위호환).
- `extract_graph` 채택 규칙에 추가: `raw in verify` ∧ `len≥MIN` ∧ `not in STOPWORDS` ∧ **(type is None or type in ENTITY_TYPES)**. (type이 허용 밖이면 폐기.) seed는 그대로 무조건.
- `ENTITY_STOPWORDS`: 보강(노조·노사·이동통신사·업계·당국·소비자·국민 등).
- 관계 로직 불변(allowed 기반) → 엔티티 정화가 관계로 전파.

## 5. Implementation Split
- relations.py 단일 파일 중심(프롬프트·파싱·필터·스톱워드) + 테스트. news-feed·consumer 배선 변경 없음(extract_graph 시그니처·반환 불변).

## 6. File Map (기계적)
- `[Mod] services/research/app/extract/relations.py` — 프롬프트 타입 형식·`_parse_graph` 타입 파싱·`extract_graph` 타입 필터·`ENTITY_STOPWORDS` 보강
- `[Mod] services/research/tests/test_relations.py` — 타입 폐기·스톱워드·하위호환·관계 정화 테스트
- `[New] doc/design/research/api-contract-extract-quality.py` · `[New] doc/decisions/0017-*.md`

## 7. Verification
- 단위(스텁 LLM): AC1 타입 폐기 / AC2 스톱워드 / AC3 하위호환(바레 문자열) / AC4 관계 정화 / 회귀(㉚ 6 + ㉛ 3 통과).
- 통합(실 스택): 재빌드 후 신규 수집 관찰 — 비종목 엔티티에 노조·일반어 신규 유입 감소(그래프 표본).
- 가드레일: 환각 0·근거 결속·엣지 5종. mypy·계약 통과.

## 8. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260724 | /design | 개방형 NER 추출 품질 — §3/§4 학습 중 실측 발견(노조·일반어 노드→관계 오염). 원인: 타입 미활용 + 스톱워드 19개. 결정: **엔티티 타입 검증(근본) + 스톱워드 보강(안전망)**, 하위호환 유지. 엔티티 정화→관계 자동 정화. 계약 `api-contract-extract-quality.py` mypy 통과. ADR 0017(ADR 0014 개방형 NER 정제). ㉜(사전 종목 태깅)와 다른 층. 기존 오염 데이터 정리는 후속. |
