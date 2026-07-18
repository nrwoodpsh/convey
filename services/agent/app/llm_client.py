"""llm-inference 서비스 클라이언트.

에이전트는 ollama를 직접 부르지 않는다 — '모델 서빙' 책임은 llm-inference 소유.
게이트웨이를 재진입하지 않고 east-west 직접 호출하되, 기존 HMAC 신뢰헤더를
그대로 붙여 llm-inference의 make_gateway_dep 검증을 통과시킨다(신뢰 패턴 재사용).
"""
from __future__ import annotations

import httpx
from common.errors import AppError
from common.security import (
    H_SIGNATURE,
    H_TIMESTAMP,
    H_USER_ID,
    H_USER_NAME,
    H_USER_ROLES,
    UserContext,
    sign_internal,
)


class LLMClient:
    def __init__(self, base_url: str, internal_secret: str) -> None:
        self._secret = internal_secret
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=httpx.Timeout(300.0))

    async def close(self) -> None:
        await self._client.aclose()

    def _trust_headers(self, user: UserContext, path: str) -> dict[str, str]:
        ts, sig = sign_internal(secret=self._secret, user_id=user.user_id, path=path)
        return {
            H_USER_ID: user.user_id,
            H_USER_NAME: user.user_name,
            H_USER_ROLES: user.roles,
            H_TIMESTAMP: ts,
            H_SIGNATURE: sig,
        }

    async def chat(self, messages: list[dict[str, str]], user: UserContext) -> str:
        path = "/chat"
        try:
            r = await self._client.post(
                path, json={"messages": messages}, headers=self._trust_headers(user, path)
            )
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError("llm_upstream", f"llm-inference 호출 실패: {exc}", status=502) from exc
        return str(r.json().get("response", ""))
