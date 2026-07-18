"""Ollama 데몬 HTTP 클라이언트 (모델 다운로드는 런타임에서 `ollama pull`)."""
from __future__ import annotations

import httpx
from common.errors import AppError


class OllamaClient:
    def __init__(self, host: str, model: str) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._host, timeout=httpx.Timeout(300.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def generate(self, prompt: str, model: str | None = None) -> str:
        payload = {"model": model or self._model, "prompt": prompt, "stream": False}
        try:
            r = await self._client.post("/api/generate", json=payload)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError("llm_upstream", f"Ollama 호출 실패: {exc}", status=502) from exc
        return str(r.json().get("response", ""))

    async def chat(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        payload = {"model": model or self._model, "messages": messages, "stream": False}
        try:
            r = await self._client.post("/api/chat", json=payload)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError("llm_upstream", f"Ollama 호출 실패: {exc}", status=502) from exc
        return str(r.json().get("message", {}).get("content", ""))
