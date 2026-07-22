# task-auto-pipeline-20260722.md

> 라운드 ⑬ (자동 양산 루프 — 이슈 선별→자동 제작). 알파4(양산). ADR 0004.
> 계약 정본 = `doc/design/issue-detector/api-contract.py`(IssueSelectedEvent 추가). 자연어 설계만.

## 1. Requirements

- **결론**: 지금은 사람이 `POST /content/generate`로 종목을 **수동** 투입해야 쇼츠가 나온다. 이슈 선별(issue-detector)과 제작(content)이 **끊겨** 있다. 이걸 이어 **"이슈 뜨면 알아서 쇼츠 생성"**을 완성한다(알파4).
- **Scenario**: issue-detector가 주기적으로 상위 이슈 종목을 `issue.selected`로 발행 → content가 소비해 **자동으로 잡 생성**(기존 파이프라인 그대로) → 근거·스크립트·음성·broll·차트 → `ready`.
- **Objective**: 사람 개입 없이 이슈→완성본(ready)까지 자동. **발행은 여전히 사람 승인**(가드레일 불변).
- **Acceptance Criteria**:
  - [ ] AC1: 계약(`IssueSelectedEvent`·`TOPIC_ISSUE_SELECTED`) contract-gate 통과
  - [ ] AC2: issue-detector가 상위 이슈를 `issue.selected`로 발행(주기·상위K·score 임계 적용)
  - [ ] AC3: content가 `issue.selected` 소비 → `start_generation`으로 **자동 잡 생성**(수동 POST와 동일 경로)
  - [ ] AC4: **스로틀** — 같은 종목을 쿨다운 내 중복 발행 안 함(무한 양산 방지)
  - [ ] AC5: 가드레일 — 자동은 생성(`ready`)까지, **발행은 사람 승인 불변**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - issue-detector 계약은 "랭킹은 이벤트 아니라 **조회 상태**"라 명시 — 이번에 **발행을 추가**하는 건 그 stance의 진화(조회는 유지, 선별만 발행). 모순 아님을 문서화.
  - issue-detector는 지금 **소비만**(producer 없음) — KafkaProducer 신설.
  - 랭킹 상태는 **in-memory·재기동 시 초기화** → 재기동 직후 저품질 랭킹으로 남발 위험 → score 임계 + 쿨다운.
  - content `content.generate`는 `job_id` 포함(자기 큐) — issue-detector가 그걸 직접 못 씀. **별도 이벤트(`issue.selected`)** + content가 `start_generation`으로 잡 생성해야.
  - 무한 양산·중복 → 스로틀 필수. A2(history_search)가 붙으면 content 레벨 중복도 방지(짝).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 트리거 방식**: 택함 = **issue-detector 주기 발행 `issue.selected` → content `start_generation`** / 기각 = issue-detector가 content API 직접 POST(결합↑)·content가 issue API 폴링(역방향 결합) / 사유 = 이벤트 주도·느슨한 결합(아키텍처 정합).
  - **결정 2 — 조회 vs 발행**: 택함 = **조회(GET /issues/today) 유지 + 선별 발행 추가** / 기각 = 조회를 발행으로 대체 / 사유 = 사람이 보는 랭킹은 그대로, 자동 트리거만 추가.
  - **결정 3 — 남발 방지**: 택함 = **score 임계 + 상위 K + 종목별 쿨다운(재발행 억제)** / 기각 = 매 주기 top-K 전량 / 사유 = 무의미·중복 양산 차단.
  - **결정 4 — 발행 게이트**: 택함 = **자동은 `ready`까지, 발행은 사람 승인 불변**(content.approved) / 기각 = 자동 발행 / 사유 = 가드레일(콘텐츠 자동 발행 금지).

## 3. UI/UX
해당 없음.

## 4. Logic

```
issue-detector (발행 루프, 주기 emit_interval):
  ranked = ranker.top(emit_top_k, window_hours, now)
  for r in ranked:
    if r.score < score_threshold: continue
    if r.ticker in cooldown(now): continue        # 스로틀
    publish issue.selected {ticker, name, score, as_of}; mark cooldown(ticker, now)

content (handle_issue 소비):
  start_generation(GenerateReq(topic=f"{name or ticker} 이슈", ticker), owner_id="auto")
    → 기존 파이프라인(content.generate → scripting → assemble → ready)
  # 발행은 사람이 approve (불변)
```
- `name` 해석: issue-detector가 종목명 알면 채우고(현재 IssueRankItem.name), 없으면 ticker.
- 쿨다운: in-memory `{ticker: last_emit_ts}`, `now - last < cooldown`이면 skip. 재기동 시 초기화(중복 몇 건 허용, A2가 보완).

## 5. Implementation Split (다음 /builder)

- **BE(issue-detector)**: worker에 **KafkaProducer + emit 루프**(top-K·score 임계·쿨다운) `asyncio.gather`로 소비 루프와 동시. config: `topic_issue_selected`·`emit_interval`·`emit_top_k`·`score_threshold`·`cooldown_seconds`.
- **BE(content)**: `consumer.handle_issue`(issue.selected → start_generation) + `run_issue_consumer`. main 등록. config `topic_issue_selected`.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] doc/design/issue-detector/api-contract.py` — IssueSelectedEvent·TOPIC (완료·mypy)
- `[Mod] services/issue-detector/app/worker.py` — emit 루프(producer·임계·쿨다운)
- `[Mod] services/issue-detector/app/main.py` — (emit 루프가 worker 백그라운드에 포함)
- `[Mod] services/issue-detector/app/config.py` — 발행 설정
- `[Mod] services/content/app/consumer.py` — handle_issue·run_issue_consumer
- `[Mod] services/content/app/main.py`·`config.py` — issue 소비자 등록·토픽

## 7. Verification (다음 /builder)

- 계약: mypy (AC1)
- issue-detector: 랭커에 이슈 주입 → emit 루프가 임계 초과 종목만 `issue.selected` 발행, 쿨다운 내 재발행 안 함(AC2·AC4) — 실 Kafka
- content: `issue.selected` 투입 → `handle_issue` → 잡 생성(pending→...), 수동 POST와 동일(AC3) — 실 content_db
- 가드레일: 자동 생성 잡도 `ready`에서 멈춤(자동 approve 없음) 확인(AC5)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 자동 양산 루프 — issue-detector 주기 발행 `issue.selected`(score 임계·쿨다운) → content `start_generation` 자동 잡. 조회 상태 유지·발행 추가. 발행은 사람 승인 불변. |
| 20260722 | /builder | issue-detector `run_emitter`(KafkaProducer + 주기·상위K·score 임계·종목 쿨다운) + main 등록 + config 발행 설정. content `handle_issue`(issue.selected→start_generation) + `run_issue_consumer` + main 등록 + config 토픽. 계약 `IssueSelectedEvent`. **검증(실 Kafka·content_db)**: emitter가 005930(score 2.3)만 발행·000660(임계미달) 제외·쿨다운 중복0(AC2·AC4), content가 소비→자동 잡 생성(pending·owner=auto)+content.generate 발행(AC3), 자동 승인 없음(AC5). mypy·contract-gate clean, 랭킹 단위 4 회귀 없음. |
