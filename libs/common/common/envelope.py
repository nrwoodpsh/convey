"""이벤트 봉투(㊱ P1) — 모든 Kafka 메시지 공통 메타 + payload.

정석 학습: 날 JSON 대신 봉투로 감싸 추적(event_id)·타입·버전·시각·발행자를 표준화한다.
발행부는 `wrap`으로 감싸고, 소비부는 `unwrap`으로 payload만 꺼낸다(핸들러는 도메인 데이터만 본다).

하위호환: `unwrap`은 봉투가 아니면(레거시 날 JSON) 그대로 반환 — 전환 중·재생(replay) 안전.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

ENVELOPE_VERSION = 1


@dataclass
class EventEnvelope:
    """공통 메타 + payload. event_id=추적·중복제거 열쇠, event_type=토픽, occurred_at=ISO8601 UTC."""

    event_id: str
    event_type: str
    version: int
    occurred_at: str
    producer: str
    payload: dict[str, Any]
    key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "version": self.version,
            "occurred_at": self.occurred_at,
            "producer": self.producer,
            "payload": self.payload,
            "key": self.key,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_envelope(
    event_type: str, payload: dict[str, Any], producer: str, key: str | None = None
) -> EventEnvelope:
    """도메인 payload를 봉투로. event_id는 UUID, occurred_at은 현재 UTC."""
    return EventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        version=ENVELOPE_VERSION,
        occurred_at=_now_iso(),
        producer=producer,
        payload=payload,
        key=key,
    )


def wrap(
    event_type: str, payload: dict[str, Any], producer: str, key: str | None = None
) -> dict[str, Any]:
    """발행용 봉투 dict. (직렬화는 kafka.py의 json/Avro가 담당.)"""
    return make_envelope(event_type, payload, producer, key).to_dict()


def is_envelope(msg: Any) -> bool:
    """봉투 구조인지 판별 — event_id·event_type·payload 3키 존재."""
    return (
        isinstance(msg, dict)
        and "payload" in msg
        and "event_id" in msg
        and "event_type" in msg
    )


def unwrap(msg: Any) -> dict[str, Any]:
    """봉투면 payload, 아니면(레거시 날 JSON) 그대로 — 소비부 하위호환."""
    if is_envelope(msg):
        payload = msg["payload"]
        return payload if isinstance(payload, dict) else {}
    return msg if isinstance(msg, dict) else {}
