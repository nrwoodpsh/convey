"""수동커밋+DLQ 소비 검증(㊱ P4) — 재시도 후 DLQ 발행·성공 시 DLQ 없음·디코딩 실패도 DLQ."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import common.kafka as kafka
from common.kafka import _process_one


class _FakeDlq:
    """KafkaProducer 대역 — publish 호출 기록."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], str | None]] = []

    async def publish(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        self.calls.append((topic, value, key))


def _raw(payload: dict[str, Any]) -> bytes:
    # 봉투 JSON(소비 이중경로의 JSON 경로) — deserializer 미사용
    return json.dumps({"event_id": "x", "event_type": "t", "version": 1, "occurred_at": "n",
                       "producer": "p", "payload": payload}).encode()


def _run(coro: Any) -> None:
    asyncio.run(coro)


def test_success_no_dlq() -> None:
    kafka._RETRY_BACKOFF = 0
    dlq = _FakeDlq()
    seen: list[dict[str, Any]] = []

    async def handler(p: dict[str, Any]) -> None:
        seen.append(p)

    _run(_process_one("t", _raw({"a": 1}), None, handler, dlq, 3, ".dlq", "k"))
    assert seen == [{"a": 1}] and dlq.calls == []  # 성공 → DLQ 없음


def test_retry_then_dlq() -> None:
    kafka._RETRY_BACKOFF = 0
    dlq = _FakeDlq()
    attempts = {"n": 0}

    async def handler(p: dict[str, Any]) -> None:
        attempts["n"] += 1
        raise ValueError("boom")

    _run(_process_one("research.ingested", _raw({"a": 1}), None, handler, dlq, 2, ".dlq", "k"))
    assert attempts["n"] == 3  # retry_max(2) + 최초 1 = 3회 시도
    assert len(dlq.calls) == 1
    topic, value, key = dlq.calls[0]
    assert topic == "research.ingested.dlq"
    assert value["original"] == {"a": 1} and value["attempts"] == 3 and "boom" in value["error"]
    assert value["source_topic"] == "research.ingested" and key == "k"


def test_decode_failure_to_dlq() -> None:
    kafka._RETRY_BACKOFF = 0
    dlq = _FakeDlq()

    async def handler(p: dict[str, Any]) -> None:  # 호출되면 안 됨
        raise AssertionError("핸들러가 불리면 안 됨")

    # Avro 매직바이트(0)인데 deserializer=None → 디코딩 실패 → DLQ
    _run(_process_one("t", b"\x00bad", None, handler, dlq, 3, ".dlq", None))
    assert len(dlq.calls) == 1 and dlq.calls[0][1]["attempts"] == 0
