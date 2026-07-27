# 20260726 — 요약: DLQ + 수동커밋 (라운드㊱ P4)

- **Task**: `doc/design/eventing/20260725-task-eventing.md` (P4, AC4) · 계약 `api-contract-eventing.py` · ADR 0019
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 단위 + 실스택
- **상태**: AC4 완료·검증. 인프라 추가 없음(코드 중심). P5(모니터링)만 남음.

## 개요

소비를 자동커밋(at-most-once, 예외 삼킴)에서 **수동커밋 + 재시도 + DLQ**(at-least-once)로 바꾼다(㊱ P4). `consume_reliable`이 메시지 처리 성공(또는 DLQ) 후에만 offset을 커밋하고, 처리 실패는 `RETRY_MAX`회 재시도 후 `{topic}.dlq`로 보낸다(poison 메시지가 파티션을 막지 않게). `consume_forever`가 이 함수에 위임해 **전 소비자가 호출부 변경 없이** 신뢰성 소비로 전환된다.

## 변경사항

- **libs/common/common/kafka.py**:
  - `consume_reliable(...)` — `enable.auto.commit=false`, poll→처리→`_commit_sync`(성공/DLQ 후 전진). 실패 시 `_process_one`이 `retry_max` 재시도(선형 백오프) 후 `_to_dlq`.
  - `_process_one` — 디코딩 실패도 DLQ(poison), 예외를 밖으로 안 던짐(offset 전진).
  - `_to_dlq` — DLQ 메시지 = `{original, error, attempts, failed_at, source_topic}`.
  - `consume_forever` → `consume_reliable` 위임(전 소비자 무변경). `RETRY_MAX`·`DLQ_SUFFIX` 상수.

## API 변경

- 소비 시맨틱: at-most-once(자동커밋·예외삼킴) → **at-least-once**(수동커밋·재시도·DLQ). 토픽·핸들러 시그니처 불변. 실패 메시지는 `{topic}.dlq`로.

## 검증

- 단위 3(+회귀 15): 성공→DLQ 없음 / 재시도 후 DLQ(attempts·error·source_topic·key) / 디코딩 실패→DLQ. mypy `--strict` 0(confluent commit 오버로드는 `_commit_sync` 헬퍼로 해소).
- **실스택**(전 kafka 서비스 재빌드):
  - DLQ 라이브: 실패 핸들러(retry_max=1)로 소비 → `p4.dlq.test2.dlq` 도달, payload=`{original:{job:1,x:y}, error:"의도적 실패", attempts:2, failed_at, source_topic}`.
  - 회귀: 7개 kafka 서비스 reliable 모드 소비(로그 `consuming(reliable) retry_max=3`) 에러 0, 그래프 노드 14,756로 증가(research가 consume_reliable로 뉴스 소비·Neo4j 적재 = 파이프라인 라이브), 대시보드 정상.

## 특이사항 (설계 대비·후속)

- **위임 설계**: `consume_forever`를 `consume_reliable`로 위임 → 5개 소비자 호출부 무변경으로 at-least-once 전환(설계의 "consume_forever 대체" 취지 충족, 블라스트 반경 0).
- **DLQ 발행**: DLQ도 봉투+Avro(KafkaProducer 재사용). 소비자별 DLQ 프로듀서 1개.
- **poison 처리**: 디코딩 실패·핸들러 재시도 초과 모두 offset 전진(파티션 안 막힘). 재투입은 사람 검수(DLQ 메시지에 원본+메타).
- **후속**: P5 Prometheus/Grafana/kafka-exporter(consumer_lag·dlq_rate 대시보드).
- 커밋: 아직(사람 게이트 — `/commit`).
