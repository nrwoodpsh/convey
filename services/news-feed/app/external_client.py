"""리서치 소스 클라이언트 (부패방지 계층).

RSS/뉴스 피드 + 외부 리서치 API를 여기서만 호출하고, 외부 스키마를 내부 표준
형태(원문+출처 URL·라이선스 메타)로 변환해 격리한다. market-feed의 패턴을 따른다.

⚠️ 지금은 stub. TODO(/builder):
  - RSS: feedparser 또는 httpx로 피드 파싱 → 항목별 원문·링크·published
  - 외부 API: httpx.AsyncClient + 인증(api_key)
  - 출처 URL·라이선스 메타는 반드시 함께 반환(가드레일).
"""
from __future__ import annotations


class ResearchSourceClient:
    def __init__(self, feed_urls: list[str], base_url: str = "", api_key: str = "") -> None:
        self._feed_urls = feed_urls
        self._base_url = base_url
        self._api_key = api_key

    async def fetch_new_documents(self) -> list[dict]:
        """신규 원문 수집 (stub). 반환 항목: {title, body, source_url, license, published}."""
        # TODO(/builder): RSS/외부 API 실제 수집으로 교체
        return []
