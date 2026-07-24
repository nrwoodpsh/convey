# ADR 0015 — 긴 기사 요약 선행 NER + LLM 출력 상한

- **상태**: 채택 (2026-07-24)
- **맥락**: 전량 백필(`app.backfill --llm`, 개방형 NER)이 **타임아웃 다발로 중단**. 실측 성공 8 / 타임아웃 9(약 17건에서 종료, 1,175 중). 원인은 일부 기사의 **긴 본문**을 로컬 LLM(llama3.2)에 통째로 넣어 생성이 기사당 240초를 초과. `OllamaClient.generate`에 **출력 길이 제한이 없음**이 근본. 라이브 NER와 백필의 Ollama 경합이 가중.
- **결정**:
  - **긴 본문(>1,500자)은 요약 선행** — 로컬 Ollama로 먼저 짧게 요약한 뒤 그 요약 위에서 개방형 NER. 짧은 본문(대부분 RSS `summary`/`description` 발췌)은 원문 그대로 NER.
  - **요약 호출에 출력 상한 강제** — llm-inference `/generate`·`OllamaClient.generate`에 `num_predict`(선택) 추가, 요약 caller는 `SUMMARY_NUM_PREDICT=256`으로 바인딩. 이것이 타임아웃 실효 제거의 핵심(프롬프트 지시만으로는 상한 미보장).
  - **환각 방지(알파1) 보존** — 요약은 LLM 생성물이라 요약 환각 엔티티가 있을 수 있음. `extract_graph`에 `verify_text`를 두어 **원문 본문에 substring 검증**(요약 아님). 원문 실재 엔티티만 채택.
  - **백필 직렬·저부하 유지** — 병렬화 금지. 요약으로 건당 시간이 줄어 라이브 NER와 경합해도 완주 가능. 수집 멱등이라 중단돼도 재개 안전.
  - **추론모델 대응(구현 중 발견)** — `.env` 실효 모델이 `qwen3:14b`(추론모델). num_predict 상한이 `<think>` 토큰만 채워 **빈 요약**을 반환(프로브 64토큰→0자·211초). 해결: 추출·요약 호출에 **`think=False`**(추론 억제)와 **`keep_alive="30m"`**(호출 사이 9.8GB 재적재 방지)를 전달. 적용 후 프로브 요약 **22초·416자**로 정상화. `think`·`keep_alive`는 llm-inference `/generate`의 선택 파라미터로 노출(미지정 시 기존 동작).
- **트레이드오프**: 긴 기사는 LLM 호출 2회(요약+NER)로 늘지만, 각 호출이 짧아져 총 시간·타임아웃은 감소. 요약이 사건·관계를 일부 누락할 수 있음(관계 회수량↓ 가능) — 대상이 "긴 기사만"이라 영향 제한, threshold·num_predict는 관측 후 조정. 유창성보다 정확·완주 우선.
- **대안(기각)**:
  - **본문 앞부분 절삭(truncate)** — 단순하지만 뒷부분 엔티티 손실. 요약이 전체 대표성 유지 → 품질 우위(사용자 선택).
  - **프롬프트 지시만("3문장 이내")** — 모델이 어기면 상한 미보장 → 타임아웃 잔존.
  - **전량 요약** — 짧은 것도 LLM콜 2배·정보손실. 대부분 이미 짧아 불필요.
  - **num_ctx 상향** — 이번 범위 밖(후속). 출력 상한이 1차 병목.
- **영향**: llm-inference(`main.py`·`ollama_client.py`) · research `extract/relations.py`(summarize·verify_text·orchestrator) · `consumer.py`·`backfill.py` 배선. 하위호환(모든 신규 파라미터 기본 None/기존 동작). 계약 `api-contract-summary-ner.py`. 텍스트 LLM은 여전히 로컬 Ollama만.
- **관련**: [0014](개방형 NER — 이 결정이 확장하는 대상), [0005](GraphRAG), [0004](알파1 정확·근거), [0006](벡터 제외). 라운드㉛.
