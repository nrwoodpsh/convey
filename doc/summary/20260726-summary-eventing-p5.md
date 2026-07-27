# 20260726 — 요약: 모니터링 Prometheus/Grafana/kafka-exporter (라운드㊱ P5)

- **Task**: `doc/design/eventing/20260725-task-eventing.md` (P5, AC5·AC6) · 계약 `api-contract-eventing.py` · ADR 0019
- **작업**: /run(builder→sync) · 2026-07-26 · main · 설정 유효성 + 실스택 데이터경로
- **상태**: AC5·AC6 완료·검증. **㊱ Kafka 정석 스택 P1~P5 전부 완료.**

## 개요

이벤트 계층 관측성을 정석 스택으로 추가한다(㊱ P5). **kafka-exporter**가 Kafka/consumer 지표를 노출하고, **Prometheus**가 스크레이프, **Grafana**가 `consumer_lag`·`throughput`·`dlq_rate` 대시보드를 자동 프로비저닝한다. 코드 변경 없음(인프라·설정만).

## 변경사항

- **docker-compose.yml**: `kafka-exporter`(danielqsj/kafka-exporter, `--kafka.server=kafka:9092`, 9308) · `prometheus`(prom/prometheus, scrape kafka-exporter) · `grafana`(grafana/grafana, 자동 프로비저닝·익명 열람).
- **infra/monitoring/**: `prometheus.yml`(scrape kafka-exporter·self) · `grafana/provisioning/datasources/prometheus.yml`(Prometheus 데이터소스) · `grafana/provisioning/dashboards/dashboards.yml`(파일 프로바이더) · `grafana/dashboards/eventing.json`(3패널: Consumer Lag·Throughput·DLQ Rate).
- **.env.example**: KAFKA_EXPORTER_PORT·PROMETHEUS_PORT·GRAFANA_PORT·GRAFANA_USER/PASSWORD.

## API 변경

- 없음(관측 인프라). 서비스 코드·이벤트 불변.

## 검증

- 설정 유효성: 대시보드 JSON(3패널)·prometheus.yml·grafana provisioning yaml 파싱 OK.
- **실스택 데이터경로**(기동):
  - kafka-exporter: `kafka_consumergroup_lag` 등 노출(실 컨슈머 그룹 content-assembled·content-generate…).
  - Prometheus: kafka-exporter target `up=1`, `consumer_lag` **22 시계열**.
  - Grafana: health `database: ok`, 대시보드 "CONVEY Eventing (㊱ Kafka)" 3패널 자동 프로비저닝, 데이터소스 Prometheus.
  - dlq_rate 소스: `.dlq` 토픽 offset 지표 관측(p4.dlq.test2.dlq).
- AC6: `enable.idempotence`·앱 멱등(source_url) 유지. 각 Phase mypy strict 0·계약 0·회귀 통과.

## 특이사항 (설계 대비·후속)

- **시각 렌더**: Grafana 대시보드의 그래프 시각화는 브라우저(localhost:3000, 익명 열람) — 데이터경로(exporter→prometheus→grafana provisioning)까지 헤드리스 검증. `consumer_lag`는 실 컨슈머 그룹으로 채워짐.
- **로컬 자원**: 컨테이너 +3(prometheus·grafana·kafka-exporter). 학습 감수(설계 명시).
- **㊱ 완결**: P1 봉투 · P2 Avro+Schema Registry · P3 Debezium 아웃박스 · P4 DLQ+수동커밋 · P5 모니터링 — 실무 정석 이벤트 스택 학습 완료. (payload 필드형 Avro·순수 프로듀서 아웃박스·알림 룰은 후속 여지.)
- 커밋: 아직(사람 게이트 — `/commit`).
