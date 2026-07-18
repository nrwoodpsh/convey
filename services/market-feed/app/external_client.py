"""외부 시세 소스 클라이언트.

⚠️ 지금은 **mock**(임의 가격 생성). 실제로는 여기서 KIS OpenAPI를 호출한다:
- REST: OAuth 토큰 발급(app_key/app_secret) → 현재가 조회
- 실시간: KIS websocket 구독 → 체결 스트림 수신
토큰 캐싱·레이트리밋·재연결을 이 클라이언트(=부패방지 계층)에 가둔다.
"""
from __future__ import annotations

import random


class ExternalMarketClient:
    def __init__(self, base_url: str, app_key: str = "", app_secret: str = "") -> None:
        self._base_url = base_url
        self._app_key = app_key
        self._app_secret = app_secret
        # TODO: httpx.AsyncClient + OAuth 토큰 발급/캐싱

    async def fetch_tick(self, symbol: str) -> dict:
        """단일 종목 현재가 조회 (mock)."""
        # TODO: 실제 KIS 현재가 API 호출로 교체
        price = round(random.uniform(50_000, 90_000), 0)
        return {"symbol": symbol, "price": price, "source": "mock"}
