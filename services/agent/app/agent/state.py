"""대화/세션 상태 — 한 요청 처리 동안의 메시지 누적."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentState:
    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
