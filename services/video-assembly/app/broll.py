"""broll 배경 — Pexels 무료 스톡(사진·영상). 부패방지 계층. 라운드⑫ (ADR 0008).

유료 생성형 영상 대신 무료 스톡으로 배경을 조달한다. 상업사용 OK. 키워드로 세로 자산 검색·
다운로드하고, **출처·작가·라이선스 메타를 함께 반환**(가드레일: 미디어 자산 출처 계승).
실패(키없음·네트워크)는 예외 대신 None → 워커가 로컬 카드로 폴백(파이프라인 보호).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

logger = logging.getLogger("video-assembly")


@dataclass
class Broll:
    """다운로드된 배경 자산 + 출처 메타."""

    path: str
    kind: Literal["photo", "video"]
    source_url: str  # Pexels 페이지(출처)
    author: str
    license: str = "Pexels"  # 상업사용 OK·표기 불요


class PexelsClient:
    """Pexels API(무료 키) — 세로 사진/영상 1건 검색·다운로드 + 메타. 실패 시 None."""

    def __init__(self, api_key: str = "") -> None:
        self._key = api_key

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if not self._key:
            return None
        try:
            resp = httpx.get(url, params=params, headers={"Authorization": self._key}, timeout=30)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Pexels 요청 실패: %s", exc)
            return None

    def _download(self, url: str, out_path: str) -> bool:
        try:
            with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            return True
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Pexels 다운로드 실패: %s", exc)
            return False

    def photo(self, query: str, out_path: str) -> Broll | None:
        data = self._get(
            "https://api.pexels.com/v1/search",
            {"query": query, "per_page": 1, "orientation": "portrait"},
        )
        photos = (data or {}).get("photos") or []
        if not photos:
            return None
        p = photos[0]
        src = p.get("src", {}).get("portrait") or p.get("src", {}).get("large")
        if not src or not self._download(str(src), out_path):
            return None
        return Broll(
            path=out_path, kind="photo",
            source_url=str(p.get("url", "")), author=str(p.get("photographer", "")),
        )

    def video(self, query: str, out_path: str) -> Broll | None:
        data = self._get(
            "https://api.pexels.com/videos/search",
            {"query": query, "per_page": 1, "orientation": "portrait"},
        )
        videos = (data or {}).get("videos") or []
        if not videos:
            return None
        v = videos[0]
        files = sorted(
            v.get("video_files", []), key=lambda f: int(f.get("height") or 0), reverse=True
        )
        link = files[0].get("link") if files else None
        if not link or not self._download(str(link), out_path):
            return None
        user = v.get("user", {})
        return Broll(
            path=out_path, kind="video",
            source_url=str(v.get("url", "")), author=str(user.get("name", "")),
        )

    def fetch(self, query: str, out_base: str, mode: str) -> Broll | None:
        """mode(video|photo|off)에 따라 배경 조달. video 실패 시 photo로 강등. off/실패 → None."""
        if mode == "off" or not self._key or not query.strip():
            return None
        if mode == "video":
            return self.video(query, f"{out_base}.mp4") or self.photo(query, f"{out_base}.jpg")
        return self.photo(query, f"{out_base}.jpg")
