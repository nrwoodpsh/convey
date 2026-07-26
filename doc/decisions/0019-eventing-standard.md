# ADR 0019 — 이벤트 표준·신뢰성 정석 스택 (학습 목적)

- **상태**: 채택 (2026-07-25)
- **맥락**: 현 Kafka 사용이 최소(날 JSON·봉투 없음·간이 아웃박스·DLQ 없음·모니터링 없음). §5 학습에서 실무 표준과 격차 확인. **사용자 목적 = 정석 패턴 학습**(트래픽·규모 대비가 아님 — 시스템이 트래픽 고려로 만든 게 아니므로 정석으로 다 넣어 익힌다).
- **결정**: 이벤트 계층을 정석 스택으로 표준화(단계 P1~P5, 크로스커팅 도메인 `eventing`):
  - **P1 이벤트 봉투** — 모든 메시지에 `event_id·event_type·version·occurred_at·producer·payload`.
  - **P2 Avro + Confluent Schema Registry** — Avro 직렬화, 스키마 중앙 등록·호환성(진화) 검증. `aiokafka`→`confluent-kafka-python` 교체. **구현(20260726 완료)**: 봉투를 Avro 레코드(메타 필드형)로, payload는 봉투 Avro의 `string`(JSON) — 다형 도메인 데이터라 이벤트별 payload 필드형 `.avsc`는 후속. 동기 confluent를 `asyncio.to_thread`로 감싸 서비스 async 시그니처 유지(호출부 무변경). subject=`<topic>-value`, 전역 호환성 BACKWARD. 레거시 JSON 이중경로 하위호환.
  - **P3 Transactional Outbox + Debezium CDC** — 발행부가 outbox 테이블 INSERT(같은 트랜잭션), Debezium이 Postgres WAL 캐치해 발행(유실 0). `wal_level=logical` + Kafka Connect.
  - **P4 DLQ + 재시도 + 수동커밋** — 성공 후 커밋(at-least-once), 실패 RETRY_MAX 후 `*.dlq`.
  - **P5 Prometheus + Grafana + kafka-exporter** — consumer_lag·throughput·dlq_rate 대시보드.
- **트레이드오프**: 정석은 무겁다 — 컨테이너 다수 추가(schema-registry·connect·debezium·prometheus·grafana·exporter), 라이브러리 교체, 발행/소비부 전면 변경. **규모엔 과하지만 학습이 목적이라 감수**(프로파일로 on/off). 앱 멱등(source_url)은 유지.
- **대안(기각)**: JSON Schema 경량 검증(정석 학습엔 부족), Polling 아웃박스 릴레이(Debezium보다 덜 정석), Burrow만(대시보드 없음), 현행 유지(학습 목적 불충족).
- **영향**: `libs/common`(봉투·직렬화·outbox·reliable 소비) + 전 발행/소비 서비스 + compose 인프라 + Postgres 설정. 단계별 커밋. 계약 `api-contract-eventing.py`.
- **관련**: [0008](데이터 소스), [0016](admin — 수집). §5 학습 산물. **주의: 이 ADR은 "학습 목적"이 전제** — 운영 규모 판단이 바뀌면 범위 재검토(일부 Phase는 배포 시로 미룰 수 있음).
