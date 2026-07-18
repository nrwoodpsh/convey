"""임베딩 클라이언트 — 텍스트를 벡터로. (Ollama의 /api/embeddings 재사용 가능)

llm-inference에 /embeddings를 추가해 위임하는 것을 권장(모델 서빙 책임 일원화).
여기서는 인터페이스만 정의하고 실제 백엔드는 붙일 때 채운다.
"""
from __future__ import annotations


class Embedder:
    def __init__(self, model: str) -> None:
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # TODO: llm-inference /embeddings 또는 ollama /api/embeddings 호출로 교체
        raise NotImplementedError("임베딩 백엔드 미연결 — RAG 사용 시 구현")
