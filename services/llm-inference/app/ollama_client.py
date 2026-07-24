"""Ollama 데몬 HTTP 클라이언트 (모델 다운로드는 런타임에서 `ollama pull`)."""
from __future__ import annotations

import httpx
from common.errors import AppError


def build_generate_payload(
    model: str,
    prompt: str,
    num_predict: int | None,
    think: bool | None = None,
    keep_alive: str | None = None,
) -> dict[str, object]:
    """Ollama /api/generate 페이로드. 지정된 옵션만 포함(미지정은 생략 → 하위호환). (㉛)

    - num_predict: 출력 토큰 상한(options.num_predict) — 요약 짧게.
    - think=False: 추론 모델(qwen3 등)의 <think> 생성 억제 — 상한 내 실답 확보·속도↑.
    - keep_alive: 모델 상주 시간(예 "30m") — 호출 사이 언로드→재적재(9.8GB) 방지.
    """
    payload: dict[str, object] = {"model": model, "prompt": prompt, "stream": False}
    if num_predict is not None:
        payload["options"] = {"num_predict": num_predict}
    if think is not None:
        payload["think"] = think
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    return payload


class OllamaClient:
    def __init__(self, host: str, model: str) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._host, timeout=httpx.Timeout(300.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
        think: bool | None = None,
        keep_alive: str | None = None,
    ) -> str:
        payload = build_generate_payload(
            model or self._model, prompt, num_predict, think, keep_alive
        )
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
