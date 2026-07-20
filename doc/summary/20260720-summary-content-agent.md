# 20260720 — 요약: content·agent 라운드③ (알파1, 진행 중)

- **Task**: `doc/design/content/task-content-agent-20260720.md` (ADR 0004·0006)
- **작업**: /run(builder) · 2026-07-20 · main · **로컬 전용**
- **상태**: 근거 스크립트 빌더(알파 핵심) 검증. content 잡 오케스트레이션은 구조적 배선 남음.

## 개요

이슈 종목의 근거 스크립트를 **템플릿 + 사실 슬롯 + LLM 연결문장**으로 생성. 수치(종가·등락률)는 **사실 데이터에서만** 슬롯으로 주입하고 LLM은 연결 문장(prose)만 쓴다 → **환각 물리 차단**(알파1). 모든 수치·사실은 인용(출처)에 결속.

## 변경사항 (BE)

- `services/agent/app/script/builder.py` — `build_script(topic, price, facts, llm)` → `Script`(sections + citations). `PriceEvidence`·`FactEvidence` TypedDict, `Citation`(출처 결속)
- `services/content/app/domains/content/{models,schemas,service,router}.py` — `GenerationJob` 상태머신 + `start_generation`·`get_job`·`approve`(ready만), `GET /jobs/{id}`·`POST /jobs/{id}/approve`

## 검증

- **결정론 단위 3 pass**:
  - LLM이 "종가 99999원" 거짓 숫자를 뱉어도 chart 슬롯은 사실값(71900)만 — 환각 차단
  - 모든 citation에 source_url(무출처 0)
  - hook은 LLM prose(수치 슬롯 없음)
- mypy --strict clean
- **실 Ollama qwen3:14b 라이브**: hook=prose, 수치=데이터(71900/2.34), 인용 출처 동반
- **실 content_db**: 잡 생성(pending)+content.generate 발행 · 미승인 approve **409 차단** · ready→approved+content.approved

## 특이사항 (후속)

- **남음**: content consumer(content.generate 픽업→잡 진행→agent 스크립트→미디어 fan-out), agent `retriever`를 research `/search` HTTP로 배선(라운드①의 GraphRAG). Kafka·agent·research 서비스 기동 시 e2e.
- 잡 상태머신·엔드포인트·근거 스크립트 빌더는 완료·검증됨.
- 도입 prose 프롬프트는 튜닝 여지("쇼츠 도입"을 종목별로 더 정확히). 수치 정확성(핵심)은 데이터 슬롯이라 불변.
