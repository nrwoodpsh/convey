"""도구 레지스트리. 새 도구는 여기 등록만 하면 에이전트가 사용 가능."""
from __future__ import annotations

from .base import Tool
from .calculator import CalculatorTool

# 에이전트가 사용할 수 있는 도구 목록 — 확장 지점
REGISTRY: dict[str, Tool] = {
    t.name: t
    for t in [
        CalculatorTool(),
        # SearchTool(), WeatherTool(), ... 추가
    ]
}

__all__ = ["Tool", "REGISTRY"]
