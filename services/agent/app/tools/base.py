"""도구 프로토콜 — 에이전트가 호출할 수 있는 함수의 계약."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str

    async def run(self, arg: str) -> str:
        """도구 실행. 입력/출력은 문자열로 단순화(필요시 스키마화)."""
        ...
