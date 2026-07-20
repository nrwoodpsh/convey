"""뉴스·공시 소스 클라이언트 (부패방지 계층) — RSS(무료)·DART(공시, 무료키). ADR 0008.

외부 스키마를 내부 표준 `{title, body, source_url, license, published_at}`로 변환·격리한다.
가드레일: 출처 URL·라이선스 메타 필수 동반.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx


def _entry_ts(entry: Any) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(
            parsed[0], parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], tzinfo=timezone.utc
        ).isoformat()
    return datetime.now(timezone.utc).isoformat()


class RssClient:
    """공개 뉴스 RSS 수집(키 없음)."""

    def __init__(self, feed_urls: list[str]) -> None:
        self._feed_urls = feed_urls

    def fetch(self, limit_per_feed: int = 10) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for url in self._feed_urls:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:limit_per_feed]:
                link = str(entry.get("link", ""))
                if not link:
                    continue  # 가드레일: 출처 없는 항목 제외
                docs.append({
                    "title": str(entry.get("title", "")),
                    "body": str(entry.get("summary", entry.get("description", ""))),
                    "source_url": link,
                    "license": "RSS",
                    "published_at": _entry_ts(entry),
                })
        return docs


def _dart_ts(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}T00:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


class DartClient:
    """DART 공시(opendart.fss.or.kr) — 무료 API 키 필요. 공시=Article/Event로 흡수(ADR 0008)."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def fetch_recent(self, page_count: int = 20) -> list[dict[str, Any]]:
        if not self._api_key:
            return []  # 키 없으면 스킵 — opendart 발급 후 활성화
        resp = httpx.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={"crtfc_key": self._api_key, "page_count": page_count},
            timeout=30,
        )
        data = resp.json()
        docs: list[dict[str, Any]] = []
        for item in data.get("list", []):
            rcept = item.get("rcept_no", "")
            docs.append({
                "title": f"{item.get('corp_name', '')} {item.get('report_nm', '')}".strip(),
                "body": str(item.get("report_nm", "")),
                "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}",
                "license": "DART",
                "published_at": _dart_ts(str(item.get("rcept_dt", ""))),
            })
        return docs
