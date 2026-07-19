"""근거 회수(RAG) — research/content의 /search를 east-west HTTP로 호출해 근거를 프롬프트에 주입.

CONVEY의 RAG는 벡터 유사도가 아니라 **GraphRAG(관계·인과) + SQL 사실조회**다(ADR 0005·0006).
회수 로직은 research 내부(Neo4j Cypher + Postgres)이고, agent는 계약(/search)만 호출한다.
저장소 직접접근 금지 — 반드시 research/content API 경유(east-west + HMAC 서명).
아직 미연결 — round③에서 실제 HTTP 호출로 구현.
"""
from __future__ import annotations


class Retriever:
    def __init__(self, research_url: str, content_url: str, top_k: int) -> None:
        self._research_url = research_url
        self._content_url = content_url
        self._top_k = top_k

    async def search(self, query: str) -> str:
        """근거 회수 후 하나의 컨텍스트 문자열로 합쳐 반환. 없으면 빈 문자열."""
        # TODO(round③): GET {research_url}/research/search?q=... (+ content /search) → 근거 조합
        return ""
