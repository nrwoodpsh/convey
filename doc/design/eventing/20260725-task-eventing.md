# 20260725-task-eventing.md

> 라운드 ㊱ (Kafka 이벤트 표준·신뢰성 — 정석 스택 학습). ADR 0019.
> 계약: `api-contract-eventing.py`. 신규 크로스커팅 도메인 `eventing`(libs/common + 전 서비스 + 인프라).
> **목적 = 실무 정석 학습**(사용자 확정) — 트래픽 대비가 아니라 패턴 습득. 단계(Phase) 분할.

## 1. Requirements

- **문제(§5 학습에서 도출)**: 현 Kafka 사용이 최소 — 봉투 없음(날 JSON)·스키마 관리 없음·간이 아웃박스(유실 창)·DLQ 없음(예외 삼킴)·모니터링 없음. 실무 표준과 격차.
- **목표**: 정석 스택으로 이벤트 계층 표준화·신뢰성 확보 + 그 과정을 학습. ①봉투 ②Avro+Schema Registry ③Debezium 아웃박스 ④DLQ+수동커밋 ⑤Prometheus/Grafana.
- **비목표**: 확장(파티션↑)은 트래픽 없으니 범위 밖. 앱 멱등(source_url)은 유지(방어 유지).
- **Acceptance Criteria**(Phase별):
  - [ ] AC1(P1): 모든 발행 메시지가 **봉투**(`event_id·event_type·version·occurred_at·producer·payload`). **검증: kafka-ui에서 메시지에 메타 존재 + 단위(봉투 생성).**
  - [ ] AC2(P2): 메시지가 **Avro**로 직렬화·**Schema Registry**에 스키마 등록, 호환성 검증 동작. **검증: registry에 subject 조회·호환성 규칙 위반 필드변경 거부.**
  - [ ] AC3(P3): 발행이 **outbox 테이블 INSERT(같은 트랜잭션)** + **Debezium**이 WAL 캐치해 발행. **검증: 서비스는 직접 publish 안 함, outbox 행 → 토픽 도달. commit~발행 유실 0(크래시 재현).**
  - [ ] AC4(P4): 소비 **수동커밋** + 실패 **RETRY_MAX 재시도 후 DLQ**(`*.dlq`). **검증: 처리 실패 메시지가 재시도 후 dlq 토픽으로, offset은 성공분만 전진.**
  - [ ] AC5(P5): **Prometheus+Grafana+kafka-exporter**로 consumer_lag 등 대시보드. **검증: Grafana에서 lag 그래프 확인.**
  - [ ] AC6(전체): 가드레일 — 앱 멱등 유지, 무출처 0·로컬 Ollama 불변. mypy·계약·기존 테스트 통과.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**(사용자 확정): 스키마 = **Avro + Confluent Schema Registry**. 아웃박스 = **Debezium CDC**. 모니터링 = **Prometheus+Grafana**(정석 기본). 단계화(P1~P5).
- **사각지대**(정석은 무거움 — 학습이라 감수):
  - **라이브러리 교체**: `aiokafka`는 Schema Registry 미내장 → **confluent-kafka-python**(Avro serializer + registry client)로 교체 필요. libs/common/kafka.py 대수술. (P2)
  - **Debezium 인프라**: Postgres **logical replication**(`wal_level=logical`) + **Kafka Connect** + Debezium 커넥터 등록 필요. compose에 connect·debezium 추가. (P3)
  - **발행 패턴 전면 변경**: 모든 발행부(news-feed·market-feed·issue-detector·content)가 **직접 publish → outbox INSERT**로. 소비부는 **자동커밋 → 수동커밋+DLQ**로. 광범위.
  - **Avro 스키마 저작**: 이벤트 타입마다 `.avsc` 작성·버전 관리. 초기 비용.
  - **순서**: P1(봉투)은 JSON에서 먼저 → P2(Avro)로 직렬화 이관. P3 전엔 직접 publish 유지, P3에서 outbox 전환.
  - **로컬 부하**: schema-registry·connect·debezium·prometheus·grafana·kafka-exporter = 컨테이너 다수 추가 → 로컬 자원↑(학습 감수, 필요시 프로파일로 on/off).

## 3. UI/UX
- 서비스 화면 변화 없음. **Grafana 대시보드**(P5)가 운영 화면으로 추가(lag·throughput·dlq).

## 4. Logic (Phase별)
- **P1 봉투**(`libs/common`): `EventEnvelope` + 발행 헬퍼가 payload를 봉투로 감싸 발행. 소비부는 봉투 언랩 → payload 핸들러.
- **P2 Avro/Registry**: `libs/common/kafka.py`를 confluent-kafka Avro serializer로. 이벤트별 `.avsc`(`libs/common/schemas/`). registry URL 설정.
- **P3 Debezium 아웃박스**: `outbox` 테이블(서비스 DB) + 발행부를 `publish_via_outbox(session, envelope)`로. compose에 Kafka Connect + Debezium outbox 커넥터. Postgres `wal_level=logical`.
- **P4 DLQ/수동커밋**: `consume_reliable(topic, group, handler, retry_max, dlq_suffix)` — 성공 후 커밋, 실패 재시도 후 `*.dlq` 발행. `consume_forever` 대체.
- **P5 모니터링**: compose에 prometheus·grafana·kafka-exporter. 대시보드(lag·throughput·dlq_rate).

## 5. Implementation Split (Phase = 라운드)
- P1 봉투(libs+전 서비스 배선) → P2 Avro/Registry(직렬화·스키마) → P3 아웃박스(테이블·Debezium·발행부) → P4 DLQ/수동커밋(소비부) → P5 모니터링(인프라). 각 독립 커밋.

## 6. File Map (기계적)
- `[Mod] libs/common/common/kafka.py` — 봉투·Avro serializer·outbox 발행·reliable 소비 (P1·P2·P3·P4)
- `[New] libs/common/common/envelope.py`·`libs/common/schemas/*.avsc` (P1·P2)
- `[New] services/*/…/outbox` 모델 + 발행부 교체 (P3)
- `[Mod] services/*/app/consumer.py` — reliable 소비 (P4)
- `[Mod] docker-compose.yml` — schema-registry·kafka-connect·debezium·prometheus·grafana·kafka-exporter (P2·P3·P5)
- `[Mod] infra/db` — `wal_level=logical`·outbox 마이그레이션 (P3)
- `[New] doc/design/eventing/api-contract-eventing.py` · `[New] doc/decisions/0019-*.md` · `[New] doc/ref/domains/05-eventing.md`

## 7. Verification (Phase별)
- P1: 봉투 메타 존재(kafka-ui)·단위. P2: registry subject·호환성 거부. P3: outbox→토픽 도달·유실 0(크래시 재현). P4: 실패→재시도→dlq, offset 성공분만. P5: Grafana lag 그래프.
- 전체: 앱 멱등 유지, mypy·계약·기존 테스트 통과. 로컬 자원 프로파일.

## 8. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /design | Kafka 정석 스택(학습). P1 봉투·P2 Avro+Schema Registry·P3 Debezium 아웃박스·P4 DLQ+수동커밋·P5 Prometheus/Grafana. 결정(사용자): Avro+Confluent Registry·Debezium CDC·Prometheus/Grafana·단계화. 사각지대: aiokafka→confluent-kafka 교체, Debezium 인프라(wal_level=logical·Connect), 발행/소비부 전면 변경, 로컬 컨테이너 다수. 목적=정석 학습(트래픽 대비 아님). 계약 mypy 통과. ADR 0019. 신규 도메인 eventing. |
