"""YouTube 업로드 부패방지 계층 — 외부(구글) 호출은 여기만. 라운드⑤·㊶(M4 C1).

가드레일:
  - 발행은 **사람 승인(content.approved) 후에만** — 호출 트리거는 consumer가 통제.
  - 기본 privacy=private(안전). 외부로 나가는 것은 mp4 + 메타(제목·설명·태그)뿐(원문 반출 금지).
  - description에 **출처·면책 계승**(알파① 근거). OAuth2 자격증명은 .env(커밋 금지).
  - 자격증명 없으면 예외(NotImplementedError) → consumer가 failed로 기록(재시도 가능, 파이프라인 보호).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("publishing.youtube")

_DISCLAIMER = (
    "본 영상은 공개 데이터를 바탕으로 CONVEY 자동 파이프라인이 제작했습니다. "
    "참고 정보이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다."
)


def build_description(title: str, sources: list[str] | None = None) -> str:
    """업로드 설명 — 제목 + 면책 + 출처 목록(가드레일: 출처·면책 계승)."""
    lines = [title.strip(), "", _DISCLAIMER]
    uniq = list(dict.fromkeys(s for s in (sources or []) if s))  # 중복 제거·순서 보존
    if uniq:
        lines += ["", "출처:"] + [f"- {s}" for s in uniq[:10]]
    return "\n".join(lines)


class YouTubeClient:
    """YouTube Data API v3 업로드 래퍼. OAuth2 refresh-token 흐름. 자격증명 없으면 미연결.

    실제 업로드는 resumable(대용량 mp4) — google-api-python-client. 반환은 영상 URL.
    """

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
        token_uri: str = "https://oauth2.googleapis.com/token",
        privacy: str = "private",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._token_uri = token_uri
        self._privacy = privacy

    @property
    def configured(self) -> bool:
        """자격증명 3종이 모두 있으면 업로드 시도 가능."""
        return bool(self._client_id and self._client_secret and self._refresh_token)

    def _build_service(self) -> object:
        """OAuth2 자격증명 → youtube v3 서비스. 지연 import(미설치·미설정 시 configured=False)."""
        from google.oauth2.credentials import Credentials  # 지연 import
        from googleapiclient.discovery import build

        creds = Credentials(  # type: ignore[no-untyped-call]  # google-auth 스텁 없음
            token=None,
            refresh_token=self._refresh_token,
            client_id=self._client_id,
            client_secret=self._client_secret,
            token_uri=self._token_uri,
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    async def upload(
        self, mp4_path: str, title: str, description: str = "", tags: list[str] | None = None
    ) -> str:
        """쇼츠 업로드 → 영상 URL. 자격증명 없으면 NotImplementedError(미연결).

        동기 google 클라이언트를 스레드로 격리(이벤트루프 비블로킹). resumable 업로드.
        """
        if not self.configured:
            raise NotImplementedError("YouTube OAuth 자격증명 없음 — 발행 승인·.env 주입 후 연결")
        import asyncio

        return await asyncio.to_thread(self._upload_sync, mp4_path, title, description, tags or [])

    def _upload_sync(
        self, mp4_path: str, title: str, description: str, tags: list[str]
    ) -> str:
        from googleapiclient.http import MediaFileUpload

        service = self._build_service()
        body = {
            "snippet": {"title": title[:100], "description": description[:4900], "tags": tags},
            "status": {"privacyStatus": self._privacy, "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(mp4_path, mimetype="video/mp4", resumable=True)
        request = service.videos().insert(  # type: ignore[attr-defined]
            part="snippet,status", body=body, media_body=media
        )
        response = None
        while response is None:
            _status, response = request.next_chunk()
        video_id = str(response["id"])
        logger.info("YouTube 업로드 완료 id=%s privacy=%s", video_id, self._privacy)
        return f"https://www.youtube.com/watch?v={video_id}"
