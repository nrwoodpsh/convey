"""Kafka Avro/봉투 경로 검증(㊱ P2) — 봉투 Avro 스키마 형태 + 레거시 JSON 하위호환 디코딩.

실제 Avro 인코딩·Registry 왕복은 실스택(Registry 필요)에서 검증. 여기선 스키마·이중경로 로직.
"""
from __future__ import annotations

import json

from common.kafka import ENVELOPE_AVRO_SCHEMA, _decode


def test_envelope_avro_schema_fields() -> None:
    """봉투 Avro 스키마 = 메타 필드형 + payload 문자열(호환성 대상)."""
    schema = json.loads(ENVELOPE_AVRO_SCHEMA)
    names = {f["name"] for f in schema["fields"]}
    assert names == {"event_id", "event_type", "version", "occurred_at", "producer", "payload", "key"}
    payload_field = next(f for f in schema["fields"] if f["name"] == "payload")
    assert payload_field["type"] == "string"  # payload는 JSON 문자열(다형 도메인)


def test_decode_legacy_json_envelope() -> None:
    """레거시 JSON 봉투(매직바이트 아님) → payload 언랩(하위호환)."""
    raw = json.dumps({
        "event_id": "x", "event_type": "t", "version": 1, "occurred_at": "n",
        "producer": "p", "payload": {"ticker": "005930"},
    }).encode()
    assert _decode(None, "t", raw) == {"ticker": "005930"}  # deserializer 미사용(JSON 경로)


def test_decode_legacy_raw_json() -> None:
    """봉투도 아닌 완전 레거시 날 JSON → 그대로."""
    raw = json.dumps({"ticker": "005930", "close": 71900}).encode()
    assert _decode(None, "t", raw) == {"ticker": "005930", "close": 71900}


def test_decode_debezium_double_encoded() -> None:
    """Debezium이 JSONB 봉투를 문자열로 이중 인코딩(㊱ P3) → 두 번 디코딩해 payload 추출."""
    envelope = {"event_id": "x", "event_type": "content.approved", "version": 1,
                "occurred_at": "n", "producer": "content",
                "payload": {"job_id": 9999, "content_id": 9999}}
    raw = json.dumps(json.dumps(envelope)).encode()  # 이중 인코딩
    assert _decode(None, "content.approved", raw) == {"job_id": 9999, "content_id": 9999}
