# 20260724-task-summary-ner.md

> 라운드 ㉛ (요약 선행 NER + LLM 출력 상한). ADR 0015.
> 계약: `api-contract-summary-ner.py`. research 도메인(추출 파이프라인). 텍스트 LLM은 로컬 Ollama만.

## 1. Requirements

- **문제**: 전량 백필(`--llm`)이 **타임아웃 다발로 중단**됨 — 실측 성공 8 / 타임아웃 9(약 17건에서 종료). 원인은 일부 기사의 **긴 본문**을 로컬 LLM(llama3.2)에 통째로 넣어 생성이 기사당 240초를 초과. `OllamaClient.generate`에 **출력 길이 제한이 없음**이 근본.
- **목표**: 긴 본문은 **로컬 요약 선행 → 요약 위에서 개방형 NER**. 요약 호출은 **출력 상한(num_predict)**을 강제해 타임아웃을 없앤다. 짧은 본문(대부분 RSS 발췌)은 그대로.
- **핵심 제약(알파1 보존)**: 요약은 LLM 생성물 → 요약에서 NER 후 **요약에** 검증하면 요약 환각 엔티티가 통과. 반드시 **원문 본문에 substring 검증**해 원문 실재 엔티티만 채택.
- **Acceptance Criteria**:
  - [x] AC1: llm-inference `/generate`가 `num_predict`(선택) 지원 — 지정 시 Ollama `options.num_predict` 전달, 미지정 시 기존과 동일(무제한). **검증: 단위(payload에 options 포함/미포함) + 실호출로 요약 출력이 상한 이하.**
  - [x] AC2: 본문 > `SUMMARY_THRESHOLD`(1,500자)면 요약 후 NER, 이하면 원문 NER. **검증: 스텁 분기 단위테스트 — 긴 본문→summarize 호출됨, 짧은 본문→호출 안 됨.**
  - [x] AC3: **환각 방지 보존** — 요약이 지어낸(원문에 없는) 엔티티는 폐기. **검증: 단위테스트 — 요약 스텁이 원문에 없는 엔티티 포함 → verify_text=원문으로 결과에서 제외.**
  - [x] AC4: 백필이 요약 경로로 **타임아웃 급감·완주 진전**. **검증: 소량(`--limit 30`) 백필에서 이전 대비 "개방형 추출 실패" 비율 대폭 감소(측정 로그).**
  - [x] AC5: 가드레일 불변 — 요약·NER 모두 로컬 Ollama만(외부 유출 0), 관계 `source_article_id` 결속, 엣지 화이트리스트, 수집 멱등 유지.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**(사용자 확정):
  - **결정 1 — 출력 상한 방식**: 택함 = **num_predict 파라미터 추가**(llm-inference `/generate`·OllamaClient) / 기각 = 프롬프트 지시만("3문장 이내" — 모델이 어기면 상한 미보장) / 사유 = 타임아웃 실효 제거. (사용자 확정)
  - **결정 2 — 요약 대상**: 택함 = **긴 것만(1,500자↑)** / 기각 = 전량(짧은 것도 LLM콜 2배·정보손실) / 사유 = 대부분 이미 짧은 발췌(RSS `summary`/`description`), 불필요 비용·품질저하 회피. (사용자 확정)
  - **결정 3 — 환각 검증 기준**: 택함 = **원문 본문에 substring 검증**(요약 아님) / 기각 = 요약에 검증(요약 환각 통과) / 사유 = 알파1(환각 0) 보존. **(설계가 못 박음 — 사용자에게 안 물음, 명백)**
  - **결정 4 — 백필 동시성**: 택함 = **직렬·저부하 유지**(현행 for 루프) / 기각 = 병렬화 / 사유 = 요약으로 건당 시간↓ → 라이브 NER와 경합해도 완주. 멱등이라 재개 안전. (사용자 확정)
- **사각지대**:
  - **num_ctx(컨텍스트 창)**: llama3.2 기본 컨텍스트가 작으면(2K~4K) 긴 본문이 잘려 요약 품질↓ 또는 prefill 지연. 이번 범위는 **출력 상한(num_predict)만** — num_ctx 튜닝은 후속(관측 후). 요약 대상이 긴 본문이라 요약 입력이 컨텍스트를 넘을 수 있음 → 요약 프롬프트가 앞부분 위주로 동작(허용, 후속에서 num_ctx 상향 검토).
  - **요약 지연 자체**: 요약도 긴 본문 prefill을 함 → 요약 출력 상한이 없으면 무의미. 상한(256)이 실효의 전제(결정 1과 결속).
  - **seed 일관성**: seed는 **원문 기준**(news-feed 태깅)이라 요약에 없어도 신뢰 유지(기존 정책). 관계 subject/object는 (검증 엔티티 ∪ seed)라 seed 관계는 유지됨.
  - **하위호환**: `extract_graph`에 `verify_text`(기본 None) 추가 → 기존 호출부(㉚ 단위테스트) 불변. `GenerateReq.num_predict`(기본 None) → 기존 호출 불변.
  - **요약 품질 편차**: 짧은 요약이 사건·관계를 누락할 수 있음 → 관계 회수량이 원문 NER보다 줄 수 있음(트레이드오프). 대상이 "긴 기사만"이라 영향 제한. 관측 후 threshold·num_predict 조정.

## 3. UI/UX

- 사용자 화면 변화 없음(백엔드 추출 품질·성능). 결과: 백필이 완주해 **그래프가 두꺼워지고**, 시나리오의 관계 문장·GraphRAG 회수가 풍부해짐(대시보드·영상에 간접 반영).

## 4. Logic

- **llm-inference** (`main.py`·`ollama_client.py`):
  - `GenerateReq`에 `num_predict`·`think`·`keep_alive`(모두 선택, 기본 None).
  - `OllamaClient.generate(prompt, model=None, num_predict=None, think=None, keep_alive=None)` — 지정된 옵션만 payload 포함(`options.num_predict`·`think`·`keep_alive`), 미지정 시 생략(기존과 동일).
  - **think=False**: qwen3 등 추론모델의 `<think>` 억제(상한 내 실답 확보). **keep_alive**: 모델 상주(재적재 방지). ← 구현 중 발견(§8 이탈), ADR 0015.
- **research 추출** (`extract/relations.py`):
  - `SUMMARY_THRESHOLD=1500`, `SUMMARY_NUM_PREDICT=256` 상수.
  - `build_summary_prompt(text)` — "핵심 사실·엔티티 보존, 새 정보 추가 금지, 3~5문장 요약. 설명 없이 요약만."
  - `summarize(text, llm) -> str` — `llm(build_summary_prompt(text))`.
  - `extract_graph(text, seed, llm, *, verify_text=None)` — 검증을 `verify = verify_text or text`로. `raw in text` → `raw in verify`. (그 외 동일.)
  - `extract_article_graph(body, seed, llm, llm_summary, *, summary_threshold=SUMMARY_THRESHOLD)`:
    - `len(body) <= threshold` → `extract_graph(body, seed, llm)`.
    - 초과 → `s = summarize(body, llm_summary)`; `extract_graph(s, seed, llm, verify_text=body)`.
- **호출 경계** (`consumer.py`·`backfill.py`):
  - `make_llm_caller(num_predict=None) -> LlmCaller` — /generate POST 본문에 `num_predict` 포함(있으면).
  - `llm = make_llm_caller()`, `llm_summary = make_llm_caller(SUMMARY_NUM_PREDICT)`. 두 caller 모두 `think=False`·`keep_alive="30m"`를 payload에 실음.
  - 기존 `extract_graph(body, entities, llm)` 호출 → `extract_article_graph(body, entities, llm, llm_summary)`로 교체.
  - backfill: 직렬 for 루프 유지(병렬화 금지).

## 5. Implementation Split (다음 /builder)

- **llm-inference**: `GenerateReq.num_predict` + `OllamaClient.generate` options 전달.
- **research/extract**: `build_summary_prompt`·`summarize`·`extract_graph(verify_text=)`·`extract_article_graph` + 상수.
- **research 배선**: `consumer.py`·`backfill.py`가 두 caller 생성 + `extract_article_graph` 사용. `make_llm_caller`(backfill의 `_llm_caller` 확장 / consumer의 caller).

## 6. File Map (기계적)

- `[Mod] services/llm-inference/app/main.py` — `GenerateReq.num_predict` 전달
- `[Mod] services/llm-inference/app/ollama_client.py` — `generate(num_predict)` → `options.num_predict`
- `[Mod] services/research/app/extract/relations.py` — `build_summary_prompt`·`summarize`·`extract_graph(verify_text)`·`extract_article_graph`·상수
- `[Mod] services/research/app/consumer.py` — 두 caller + `extract_article_graph` 배선
- `[Mod] services/research/app/backfill.py` — `_llm_caller(num_predict)` + `extract_article_graph`(직렬 유지)
- `[New] doc/design/research/api-contract-summary-ner.py` · `[New] doc/decisions/0015-*.md`

## 7. Verification (다음 /builder)

- 단위(스텁 LLM):
  - `num_predict` payload 분기(OllamaClient) — 지정/미지정.
  - `extract_graph(verify_text=원문)` — 요약 스텁이 원문에 없는 엔티티 포함 → 폐기(AC3).
  - `extract_article_graph` 분기 — 긴 본문→summarize 스텁 호출·요약 위 NER, 짧은 본문→요약 미호출(AC2).
- 통합(실 스택): 소량 백필 `--limit 30` → "개방형 추출 실패" 비율 이전(≈50%) 대비 급감(AC4). 그래프 노드/관계 증가.
- 가드레일: 무출처 관계 0, 로컬 Ollama만, 멱등 유지. mypy·계약·기존 단위테스트(㉚ 6개) 통과.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260724 | /builder | 구현·검증. llm-inference: `build_generate_payload`·`GenerateReq`(num_predict·think·keep_alive)·`OllamaClient.generate(...)`. research: `SUMMARY_THRESHOLD/NUM_PREDICT`·`build_summary_prompt`·`summarize`·`extract_graph(verify_text=)`·`extract_article_graph`. consumer·backfill: `_llm_caller(num_predict)` 두 caller(+`think=False`·`keep_alive=30m` 바인딩) + orchestrator(직렬). **검증**: 단위 12/12(research 8·llm-inference 4), mypy --strict 0, 계약 통과. 실스택(재빌드 후): `--limit 10` **완주·타임아웃 0**(이전 9/17≈53%→0), 그래프 173→215. **이탈(설계 결함 발견→정지→사용자 결정)**: `.env` 모델이 `qwen3:14b`(추론모델)라 num_predict 상한이 `<think>`만 채워 **빈 요약**(프로브 64토큰→0자·211초). 사용자 결정=**think 끄기+keep_alive 고정**. 적용 후 프로브 요약 **22초·416자**(211초·0자 대비 해결). AC1~5 충족. |
| 20260724 | /design | 요약 선행 NER + LLM 출력 상한. 결정: num_predict 추가(프롬프트 지시만 기각)·긴 것만 1,500자↑ 요약(전량 기각)·**원문 검증**(알파1 보존)·백필 직렬 유지. 계약 `api-contract-summary-ner.py` mypy 통과. ADR 0015. 사각지대: num_ctx는 후속, 요약 품질 편차(관계 회수 감소 가능) — 대상이 긴 기사라 제한. |
