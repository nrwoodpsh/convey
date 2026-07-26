# 20260726 — 요약: 이벤트 봉투 (라운드㊱ P1)

- **Task**: `doc/design/eventing/20260725-task-eventing.md` (P1, AC1) · 계약 `api-contract-eventing.py` · ADR 0019 · 도메인 `doc/ref/domains/05-eventing.md`
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 단위 + 실스택
- **상태**: AC1 완료·검증. Kafka 정석 스택의 첫 단계(봉투) — P2~P5(Avro·Debezium·DLQ·모니터링)는 후속.

## 개요

Kafka 메시지를 날 JSON에서 **이벤트 봉투**로 표준화한다(㊱ P1, 정석 학습). 발행부는 payload를 봉투(`event_id·event_type·version·occurred_at·producer·payload·key`)로 감싸고, 소비부는 `consume_forever`가 자동으로 언랩해 핸들러엔 payload(도메인 데이터)만 넘긴다 — 기존 핸들러 코드는 무변경.

## 변경사항

- **`libs/common/common/envelope.py`**(신규): `EventEnvelope` dataclass + `wrap(event_type, payload, producer, key)`(event_id=UUID·occurred_at=UTC ISO8601) + `unwrap(msg)`(봉투면 payload, 아니면 레거시 raw 그대로) + `is_envelope`.
- **`libs/common/common/kafka.py`**: `KafkaProducer(bootstrap, producer_name)` — publish가 payload를 봉투로 감싸 발행(event_type=topic, Kafka 파티션 키 유지). `consume_forever`가 핸들러 호출 전 `unwrap`.
- **발행부 7서비스** producer_name 배선: research·market-feed·news-feed·issue-detector·content·video-assembly·sample-domain.

## API 변경

- Kafka 메시지 포맷: 날 JSON → 봉투(payload 내부에 도메인 데이터). 토픽·키·핸들러 시그니처 불변(언랩이 중앙 처리). 하위호환: 레거시 raw 메시지도 unwrap 통과.

## 검증

- 단위 4: wrap 메타 생성·unwrap payload 추출·레거시 raw 하위호환·event_id 유일성. mypy `--strict` 0(envelope·kafka), 계약 mypy 0.
- **실스택**(전 kafka 서비스 재빌드):
  - on-the-wire: content 발행 → 날 컨슈머 raw 확인 → 봉투(event_type·version=1·producer=content·event_id 36자 UUID·key) + payload 보존.
  - 소비 언랩: `consume_forever` 핸들러가 payload만 수신(`event_id` 없음).
  - 전 kafka 서비스(research·news-feed·video-assembly·publishing·content·issue-detector·market-feed) 재빌드·기동 후 소비 에러 0.

## 특이사항 (설계 대비·후속)

- **일관성 요구**: 봉투는 전 서비스 동시 적용 필요 — 재빌드된 발행자의 봉투를 구(舊) 소비자(언랩 없음)가 못 읽어 깨진다. 그래서 전 kafka 서비스를 함께 재빌드(부분 롤아웃 시 소비자 먼저). unwrap의 raw 하위호환은 토픽에 남은 레거시 메시지 재생용.
- **범위(후속 Phase=라운드)**: P2 Avro+Schema Registry(confluent-kafka 교체)·P3 Debezium 아웃박스(wal_level=logical·Connect)·P4 DLQ+수동커밋·P5 Prometheus/Grafana — 각 인프라 컨테이너 추가 필요.
- **가드레일**: 앱 멱등(source_url) 유지, `enable_idempotence=True` 유지. 목적=정석 학습(트래픽 대비 아님).
- 커밋: 아직(사람 게이트 — `/commit`).
