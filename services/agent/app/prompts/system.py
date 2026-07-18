"""시스템/에이전트 프롬프트 템플릿 — 코드에서 프롬프트를 분리해 버전 관리.

프롬프트는 raw string으로 흩어놓지 말고 여기서 조립한다(그래야 A/B·튜닝·리뷰 가능).
"""
from __future__ import annotations

SYSTEM_PROMPT = """너는 유능한 한국어 AI 어시스턴트다.
- 모르면 모른다고 답한다.
- 제공된 컨텍스트가 있으면 그것을 우선 근거로 삼는다.
"""


def build_system_prompt(context: str | None = None) -> str:
    """RAG 검색 결과(context)를 시스템 프롬프트에 주입."""
    if not context:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\n[참고 컨텍스트]\n{context}\n"
