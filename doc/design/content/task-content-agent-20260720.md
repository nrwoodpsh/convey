# task-content-agent-20260720.md

> 라운드 ③ (근거 스크립트, 알파1). 계약 정본 = `api-contract.py`. 자연어 설계만.

## 1. Requirements

- **Scenario**: 사람이 이슈 종목으로 `POST /content/generate`. `content`가 잡을 만들고, `agent`가 `research`/`content` `/search`로 근거를 모아 **출처·수치가 인용된 스크립트**를 생성한다.
- **Objective**: 모든 수치가 출처에 못박힌 스크립트를 만든다(환각 금지 = 알파1). agent는 저장소를 직접 보지 않고 `/search`(GraphRAG)만 호출한다.
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract.py`가 contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: `Script`의 모든 수치가 `Citation`(source_url + ref_id)에 결속 — 무출처 수치 0
  - [ ] AC3: `POST /content/generate` → job 생성(202), `GET /content/jobs/{id}`로 상태 조회
  - [ ] AC4: agent가 저장소 직접접근 없이 `research/content /search` **HTTP 호출**로만 근거 회수
  - [ ] AC5: 정확 수치는 `data_slots`에 사실값으로 채워짐(LLM이 수치를 생성하지 않음)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - `content` consumer는 골격만(`handle_generate` 로그뿐). 잡 상태머신·agent 호출 미배선.
  - agent `retriever`는 HTTP 근거회수 스텁(라운드①에서 벡터 제거·재작성됨) — 실제 `/search` 호출 미구현.
  - LLM이 `data_slots`(수치)를 채우게 하면 환각 진입 — 수치는 **사실에서만** 주입.
- **핵심 결정**:
  - **결정 1 — 스크립트 생성 방식**: 택함 = **템플릿 + 사실 슬롯 + LLM 연결문장**(수치는 슬롯에 사실값 주입 → 물리적 환각 차단) / 기각 = LLM 자유생성(수치까지 LLM) / 사유 = "안 틀리는 금융 콘텐츠"(알파1). *사용자 제안 반영.*
  - **결정 2 — 근거 회수 경로**: 택함 = agent → `research/content /search` **east-west HTTP**(GraphRAG) / 기각 = agent가 DB 직접 / 사유 = 경계·계약 불변(ADR 0005)
  - **결정 3 — 잡 구동**: 택함 = `POST /generate`가 잡 큐잉 → `content.generate` consumer 픽업(비동기) / 기각 = 동기 생성 / 사유 = 양산·재개(알파4) 대비

## 4. Logic

1. `POST /content/generate` → `GenerationJob`(pending) 커밋 → `content.generate` 발행 → 202 `{job_id}`
2. consumer 픽업 → status=scripting → agent 호출
3. agent: `GET /research/search`(관계·사실) + `GET /content/search`(히스토리 중복회피) → 근거 수집 → **템플릿에 사실 슬롯 주입** + 연결 문장(로컬 LLM) → `Script`(sections + citations)
4. 스크립트 저장 → status=media (라운드④로) — 이번 라운드는 여기까지
5. `POST /content/{id}/approve` → status=approved → `content.approved` 발행(사람 승인)

## 6. File Map (기계적)

- `[New] doc/design/content/api-contract.py` — 계약 (작성 완료·mypy 통과)
- `[Mod] services/content/app/domains/content/{models,service,repository,schemas,router}.py` — 잡 상태머신·Script·Citation·조회/승인 엔드포인트
- `[Mod] services/content/app/consumer.py` — `content.generate` → 잡 진행·agent 호출
- `[Mod] services/agent/app/rag/retriever.py` — `research/content /search` 실제 HTTP 호출 구현
- `[New] services/agent/app/prompts/` — 스크립트 템플릿(사실 슬롯 + 인용 강제)
- `[Mod] services/content/app/config.py` — `research_url` 추가(히스토리·근거)

## 7. Verification

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(`/builder`): generate → job 202, 스크립트의 모든 수치에 citation 존재(AC2), agent에서 DB 접속 코드 grep 0(AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260720 | /design | 최초 설계 — 템플릿+사실슬롯 스크립트, HTTP 근거회수 (알파1) |
