# 20260726 — 요약: Avro + Schema Registry (라운드㊱ P2)

- **Task**: `doc/design/eventing/20260725-task-eventing.md` (P2, AC2) · 계약 `api-contract-eventing.py` · ADR 0019
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 단위 + 실스택
- **상태**: AC2 완료·검증. 사용자 결정 = **실무 정석(confluent-kafka + Confluent Schema Registry)**. P3~P5는 후속.

## 개요

Kafka 전송을 aiokafka → **confluent-kafka**로 교체하고 메시지를 **Avro**로 직렬화해 **Confluent Schema Registry**에 스키마를 등록·호환성 검증한다(㊱ P2). 봉투(P1)는 유지 — Avro 레코드로 표현. 서비스 호출부(`publish`/`consume_forever`)의 async 시그니처는 그대로(동기 confluent를 `asyncio.to_thread`로 격리)라 발행/소비 코드는 무변경.

## 변경사항

- **docker-compose.yml**: `schema-registry`(confluentinc/cp-schema-registry 7.7.0, 우리 KRaft Kafka에 연결, 호스트 8085·컨테이너 8081) + kafka-ui registry 연동 + 8개 kafka 서비스 `depends_on: schema-registry(healthy)`.
- **libs/common/common/kafka.py**: confluent-kafka Producer/Consumer + `AvroSerializer`/`AvroDeserializer` + `SchemaRegistryClient`. 봉투 Avro 스키마(`ENVELOPE_AVRO_SCHEMA` — 메타 필드형 + payload JSON 문자열). 발행=Avro 인코딩, 소비=이중경로 디코딩(Avro 매직바이트 0 vs 레거시 JSON `{`)으로 하위호환. 동기 호출 `asyncio.to_thread` 격리.
- **libs/common/pyproject.toml**: `aiokafka` → `confluent-kafka[schemaregistry,avro]>=2.5`.
- **libs/common/common/config.py**: `schema_registry_url` 추가. **.env.example**: `SCHEMA_REGISTRY_PORT=8085`.

## API 변경

- 메시지 와이어 포맷: JSON 봉투 → **Avro 봉투**(Registry subject=`<topic>-value`). 토픽·키·핸들러 시그니처 불변.
- 하위호환: 레거시 JSON 메시지도 소비 이중경로로 처리.

## 검증

- 단위 7: 봉투 Avro 스키마 필드·payload 문자열형·이중경로(레거시 JSON 봉투/날것) + 봉투(P1) 회귀. mypy `--strict` 0.
- **실스택**(단계적 de-risk):
  - 인프라: schema-registry healthy·API(subjects·BACKWARD 호환성)·confluent-kafka[schemaregistry,avro] 설치·import.
  - 로컬 Avro 왕복(호스트→localhost:29092/8085): 발행→소비 payload 보존(nested dict).
  - **Registry 등록**: subject `<topic>-value` 생성, 봉투 필드 스키마.
  - **호환성 거부(AC2 핵심)**: `version` int→string 변경 등록 시도 → `{"is_compatible":false}`(BACKWARD 규칙).
  - 8개 kafka 서비스 재빌드(confluent-kafka 휠)·기동 → 소비 에러 0.
  - 실 서비스 코드(content 컨테이너) Avro 왕복 + **실 도메인 subject**(`market.ticks-value`·`research.macro-value` = 실제 market-feed·research 발행) 등록 + 그래프 노드 14,121로 증가(파이프라인 Avro 라이브) + 대시보드 정상.

## 특이사항 (설계 대비·후속)

- **payload = JSON-in-Avro**: 봉투는 필드형 Avro(호환성 대상), payload는 다형 도메인이라 Avro `string`(JSON). 이벤트별 payload 필드형 `.avsc`는 후속(AC2 "필드변경 거부"는 봉투 메타 필드로 시연).
- **async 유지**: confluent는 동기·C(librdkafka)지만 `asyncio.to_thread`로 감싸 서비스 async 시그니처·호출부 무변경 → 블라스트 반경 최소화(설계의 "kafka.py 대수술"을 libs/common 국소화).
- **일관성**: Avro 소비자는 Avro 와이어를 기대 — 전 kafka 서비스 동시 재빌드 필요(구 JSON 소비자는 Avro 못 읽음). 이중경로는 토픽에 남은 레거시 JSON 재생용.
- **로컬 자원**: schema-registry 컨테이너 +1(cp 이미지 ~1GB). 호스트 8081 점유 회피로 8085 매핑.
- **후속(Phase=라운드)**: P3 Debezium 아웃박스(wal_level=logical·Connect)·P4 DLQ+수동커밋·P5 Prometheus/Grafana.
- 커밋: 아직(사람 게이트 — `/commit`).
