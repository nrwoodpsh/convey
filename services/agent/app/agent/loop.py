"""에이전트 실행 루프 — 이미지의 executor.py에 해당하는 핵심 두뇌.

흐름: (RAG 검색) → 프롬프트 조립 → LLM 호출 → (도구 필요 시 실행 후 재호출) → 응답.
LLM 호출 횟수 = 비용이므로 max_steps로 반드시 상한을 둔다.

주의: 지금은 '단일 응답' 원형이다. 실제 tool-calling(모델이 도구를 스스로 선택)은
llm-inference가 function-calling/JSON 모드를 지원하도록 확장한 뒤 이 루프에서 파싱한다.
"""
from __future__ import annotations

import logging

from common.security import UserContext

from app.agent.memory import Memory
from app.agent.state import AgentState
from app.llm_client import LLMClient
from app.prompts.system import build_system_prompt
from app.rag.retriever import Retriever

logger = logging.getLogger("agent")


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        memory: Memory,
        retriever: Retriever | None,
        max_steps: int,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._retriever = retriever
        self._max_steps = max_steps

    async def run(self, session_id: str, user_message: str, user: UserContext) -> str:
        state = AgentState(session_id=session_id, messages=self._memory.load(session_id))

        # 1) RAG — 관련 컨텍스트 검색(선택)
        context = ""
        if self._retriever is not None:
            context = await self._retriever.search(user_message)

        # 2) 프롬프트 조립 (첫 턴에만 시스템 프롬프트 삽입)
        if not any(m["role"] == "system" for m in state.messages):
            state.messages.insert(0, {"role": "system", "content": build_system_prompt(context)})
        state.add("user", user_message)

        # 3) LLM 호출 (+ 향후 도구 루프 자리) — max_steps 상한
        answer = ""
        for step in range(self._max_steps):
            answer = await self._llm.chat(state.messages, user)
            # TODO: answer에서 도구 호출 지시를 파싱해 REGISTRY 실행 후 재호출.
            #       도구 호출이 없으면(=최종 답) 루프 종료. 지금은 1스텝에 종료.
            logger.info("step=%s 완료", step)
            break

        state.add("assistant", answer)
        self._memory.save(session_id, state.messages)
        return answer
