# 도메인: eventing (이벤트 표준·신뢰성)

> 크로스커팅 도메인 — 특정 비즈니스가 아니라 **서비스 간 이벤트(Kafka)의 표준·신뢰성**을 담당. ADR 0019, 라운드㊱. **학습 목적**(정석 스택).

## 경계 (무엇을 소유하나)
- **이벤트 봉투 표준**: `event_id·event_type·version·occurred_at·producer·payload` (libs/common).
- **직렬화·스키마**: Avro + Confluent Schema Registry(호환성·진화).
- **발행 신뢰성**: Transactional Outbox + Debezium CDC(유실 0).
- **소비 신뢰성**: 수동커밋 + 재시도 + DLQ(at-least-once).
- **관측**: Prometheus + Grafana + kafka-exporter(lag·throughput·dlq).

## 경계 밖 (무엇을 안 하나)
- 도메인 로직(research·content·publishing·admin) — 이벤트 **내용**은 각 도메인 것. eventing은 **전달 방식·신뢰성**만.
- 파티션 확장·용량계획(트래픽 규모 문제 — 현재 범위 밖).

## 관계
- **모든 서비스**가 이 표준으로 발행/소비(libs/common 경유).
- 인프라: Kafka + schema-registry + kafka-connect/debezium + prometheus/grafana/kafka-exporter.
- 앱 레벨 멱등(source_url 등)은 각 도메인이 유지(중복 방어 이중화).
