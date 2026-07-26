# 20260726 — 요약: 트랜잭션 아웃박스 + Debezium CDC (라운드㊱ P3)

- **Task**: `doc/design/eventing/20260725-task-eventing.md` (P3, AC3) · 계약 `api-contract-eventing.py` · ADR 0019
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 단위 + 실스택
- **상태**: AC3 완료·검증. 범위 = **content 대표 아웃박스**(사용자 결정). 순수 프로듀서·타 서비스는 후속.

## 개요

발행을 "직접 producer.publish"에서 **트랜잭션 아웃박스**로 전환한다(㊱ P3). `content.approve`가 비즈니스 저장(job.status=approved)과 **같은 트랜잭션**에 봉투를 `outbox` 테이블로 INSERT하고, **Debezium**이 Postgres WAL을 캐치해 토픽으로 발행한다. 커밋되면 이벤트는 DB에 있으므로 앱이 커밋 직후 크래시해도 반드시 발행된다(**commit~발행 유실 0**).

## 변경사항

- **docker-compose.yml**: postgres `command: wal_level=logical`(+max_wal_senders/slots) · `kafka-connect`(debezium/connect:3.0.0.Final, REST 8083) · 헬스체크.
- **services/content**: `outbox` 테이블(마이그레이션 `e3f4a5b60013`, Debezium 기본 컬럼명 aggregatetype·aggregateid·type·payload) + `outbox.py`(`Outbox` 모델 + `publish_via_outbox(session, ...)` — 봉투를 같은 트랜잭션에 add). `service.approve`: 직접 publish 제거 → 아웃박스 INSERT + job.status 원자 커밋.
- **infra/debezium/content-outbox-connector.json**: PostgresConnector(pgoutput) + Outbox EventRouter(`route.by.field=type`→토픽, `table.field.event.payload=payload`, `expand.json.payload=true`).
- **libs/common/common/kafka.py**: `_decode`에 Debezium 이중 인코딩(JSONB→문자열) 방어(두 번 디코딩).

## API 변경

- content.approved 발행 경로: content 직접 publish → **outbox → Debezium**. 토픽·메시지 payload(봉투) 불변. 소비자(publishing) 무변경.

## 검증

- 단위 5: 봉투 Avro 스키마·이중경로·**Debezium 이중 인코딩** 디코딩(+P1 봉투 회귀). mypy `--strict` 0.
- **실스택**(단계적 de-risk):
  - 인프라: `wal_level=logical` 적용·Debezium 이미지(2.32GB)·PostgresConnector 플러그인·커넥터 등록 RUNNING.
  - **유실 0 본질**: 아웃박스 행 직접 INSERT(앱 발행 경로 미사용) → Debezium이 content.approved로 발행(앱이 발행 안 해도 DB 행만으로 토픽 도달).
  - **실 e2e**: ready 잡(job56) 발행 승인 → outbox 행(type=content.approved·aggregateid=56) job.status와 원자 커밋 → Debezium → publishing 소비 → `publish_records` content38=failed(무자격증명, 예상).
  - 이중 인코딩: `expand.json.payload=true`로 Debezium이 봉투를 객체로 발행, `_decode`가 객체·문자열 두 경우 모두 payload 추출.

## 특이사항 (설계 대비·후속)

- **이탈(Debezium 인코딩)**: Debezium이 JSONB payload를 문자열로 이중 인코딩 → `expand.json.payload=true`(커넥터) + `_decode` 이중 디코딩 방어(소비자)로 해소.
- **커넥터 등록**: Kafka Connect REST로 등록(`infra/debezium/content-outbox-connector.json`). 설정은 `_connect_configs` 토픽에 보존(Connect 재기동엔 유지) — 신규 클러스터(볼륨 초기화)는 재등록 필요(ops 스텝).
- **범위**: content만 아웃박스(교과서적 사례 = 비즈니스 트랜잭션+이벤트 원자성). 순수 프로듀서(market-feed·news-feed 등, 트랜잭션 없음)·타 서비스 아웃박스는 후속.
- **로컬 자원**: kafka-connect 컨테이너 +1(2.32GB). postgres 재시작(wal_level, pgdata 유지).
- **후속(Phase=라운드)**: P4 DLQ+수동커밋 · P5 Prometheus/Grafana.
- 커밋: 아직(사람 게이트 — `/commit`).
