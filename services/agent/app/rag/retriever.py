"""벡터 검색 — 질문과 관련된 문서 조각을 가져와 프롬프트에 주입(RAG).

저장소는 선택: postgres+pgvector(기존 postgres 재사용) 또는 전용 벡터DB(qdrant 등).
아직 미연결 — 붙일 때 아래를 구현하고 config에 접속정보 추가.
"""
from __future__ import annotations

from app.rag.embeddings import Embedder


class Retriever:
    def __init__(self, embedder: Embedder, top_k: int) -> None:
        self._embedder = embedder
        self._top_k = top_k

    async def search(self, query: str) -> str:
        """관련 문서를 검색해 하나의 컨텍스트 문자열로 합쳐 반환. 없으면 빈 문자열."""
        # TODO: embed(query) → 벡터DB top_k 검색 → 텍스트 조합
        return ""
