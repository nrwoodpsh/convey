"""타입 계약 — 이벤트 표준·신뢰성(정석 스택). 라운드㊱. ADR 0019.

검증: python -m mypy --strict --ignore-missing-imports api-contract-eventing.py

목적(학습): Kafka를 실무 정석으로 — ①이벤트 봉투 ②Avro+Schema Registry ③Debezium 아웃박스
④DLQ+수동커밋 ⑤Prometheus/Grafana 모니터링. 크로스커팅 도메인 eventing(libs/common + 전 서비스 + 인프라).
※ 규모가 아니라 **정석 학습**이 목적(사용자 확정) — 트래픽 대비 아님.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

ENVELOPE_VERSION = 1
DLQ_SUFFIX = ".dlq"        # 예: research.ingested.dlq
RETRY_MAX = 3              # 소비 재시도 후 DLQ


# ── P1. 이벤트 봉투(envelope) — 모든 메시지 공통 메타 + payload ──
@dataclass
class EventEnvelope:
    event_id: str          # UUID — 추적·중복제거 열쇠
    event_type: str        # 예: "research.ingested"
    version: int           # 스키마 버전(진화)
    occurred_at: str       # ISO8601 UTC
    producer: str          # 발행 서비스명
    payload: dict[str, Any]  # 도메인 데이터(Avro 스키마 대상)
    key: str | None = None   # 파티션·순서 열쇠


# ── P2. Avro + Schema Registry ──
class AvroCodec(Protocol):
    """Schema Registry 연동 직렬화 — payload를 등록 스키마(.avsc)로 Avro 인코딩.

    호환성(backward/forward) 검증은 Registry가 담당. 스키마 진화 시 version↑.
    libs/common/kafka.py의 json 직렬화를 대체(confluent-kafka Avro serializer).
    """

    def encode(self, subject: str, payload: dict[str, Any]) -> bytes: ...
    def decode(self, data: bytes) -> tuple[str, dict[str, Any]]: ...  # (schema_subject, payload)


# ── P3. Transactional Outbox (Debezium CDC) ──
@dataclass
class OutboxRow:
    """서비스가 비즈니스 저장과 **같은 트랜잭션**에 INSERT. Debezium이 WAL에서 캐치해 발행.

    유실 0: commit되면 outbox 행도 커밋 → Debezium이 반드시 발행. (앱은 직접 publish 안 함.)
    """

    id: str                # UUID (= event_id)
    aggregate_type: str    # 예: "content_job"
    aggregate_id: str      # 예: job_id
    event_type: str        # 라우팅용 (= topic)
    payload: dict[str, Any]
    created_at: str


class PublishViaOutbox(Protocol):
    """직접 producer.publish 대신 outbox 테이블 INSERT(같은 트랜잭션). Debezium이 발행 담당."""

    def __call__(self, session: Any, envelope: EventEnvelope) -> None: ...


# ── P4. DLQ + 재시도 + 수동커밋 (at-least-once) ──
class ConsumeReliable(Protocol):
    """수동 커밋 소비 — 성공해야 offset commit. 실패는 RETRY_MAX 재시도 후 DLQ로.

    (기존 consume_forever: 자동커밋·예외삼킴 = at-most-once → 이걸로 대체.)
    """

    def __call__(
        self,
        topic: str,
        group_id: str,
        handler: Any,  # Callable[[EventEnvelope], Awaitable[None]]
        *,
        retry_max: int = RETRY_MAX,
        dlq_suffix: str = DLQ_SUFFIX,
    ) -> Any: ...


@dataclass
class DlqRecord:
    """DLQ 메시지 — 원본 + 실패 메타(사람 검수·재투입용)."""

    original: EventEnvelope
    error: str
    failed_at: str
    attempts: int


# ── P5. 모니터링(정석) — Prometheus + Grafana + kafka-exporter ──
# compose에 prometheus·grafana·kafka-exporter 추가. 핵심 대시보드 지표(정석):
MONITOR_METRICS: tuple[str, ...] = (
    "consumer_lag",        # ⭐ 그룹·파티션별 밀림
    "throughput",          # 초당 메시지
    "partition_skew",      # hot partition
    "under_replicated",    # ISR
    "dlq_rate",            # DLQ 유입률
)

STANDARD_NOTE = (
    "봉투(P1)→Avro/Registry(P2)→Debezium 아웃박스(P3)→DLQ/수동커밋(P4)→Prometheus/Grafana(P5). "
    "libs/common 이벤트 표준 + 전 서비스 발행/소비 교체 + compose 인프라(schema-registry·connect·debezium·"
    "prometheus·grafana·kafka-exporter). 앱 멱등(source_url)은 유지(중복 방어)."
)
