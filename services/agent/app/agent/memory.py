"""대화 메모리 — 세션별 이전 대화 보관.

지금은 프로세스 메모리(인메모리)라 재시작/다중 인스턴스에 취약.
운영에서는 Redis 또는 postgres로 교체(세션 영속화). 인터페이스는 유지.
"""
from __future__ import annotations


class Memory:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, str]]] = {}

    def load(self, session_id: str) -> list[dict[str, str]]:
        return list(self._store.get(session_id, []))

    def save(self, session_id: str, messages: list[dict[str, str]]) -> None:
        # TODO: Redis/postgres로 교체 (다중 인스턴스 대비)
        self._store[session_id] = messages
