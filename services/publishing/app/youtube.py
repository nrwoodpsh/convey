"""YouTube 업로드 부패방지 계층 — 외부 호출은 여기만. 라운드⑤.

OAuth 토큰은 .env(발행 승인 후에만, 커밋 금지). 외부로 나가는 것은 mp4+메타만(원문 반출 금지).
"""
from __future__ import annotations


class YouTubeClient:
    def __init__(self, token: str = "") -> None:
        self._token = token

    async def upload(
        self, mp4_path: str, title: str, description: str = "", tags: list[str] | None = None
    ) -> str:
        """쇼츠 업로드 → 외부 URL 반환. TODO: google-api-python-client 연결."""
        if not self._token:
            raise NotImplementedError("YouTube OAuth 토큰 없음 — 발행 승인·토큰 주입 후 연결")
        raise NotImplementedError("YouTube 업로드 미연결 — google-api-python-client 배선 필요")
