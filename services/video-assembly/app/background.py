"""배경 라이브러리 선택(㊴) — 운영자 등록 배경을 admin에서 조회, 섹터/태그 매칭.

우선순위(auto): ①admin 라이브러리 섹터/태그 매칭 → ②생성(image-gen, ㊴ P2) → ③Pexels(stock)
→ ④로컬 카드. broll(Pexels)이 종목과 무관하던 문제(§7) 해소가 목적.

가드레일: 자산 라이선스 메타 계승(선택된 배경의 license를 합성 회신에 기록). admin_db 직접접근 금지(API만).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal
from common.stocks import sector_of, stock_name

from app.config import settings

logger = logging.getLogger("video-assembly")


@dataclass
class LibraryBackground:
    """선택된 라이브러리 배경 — 합성 입력 + 라이선스 메타."""

    path: str
    kind: str          # image | video
    name: str
    license: str


def fetch_backgrounds() -> list[dict[str, Any]]:
    """admin GET /admin/backgrounds(HMAC) → 자산 목록. 실패 시 빈 목록(폴백)."""
    path = "/admin/backgrounds"
    ts, sig = sign_internal(
        secret=settings.gateway_internal_secret, user_id="video-assembly", path=path
    )
    headers = {H_USER_ID: "video-assembly", H_TIMESTAMP: ts, H_SIGNATURE: sig}
    try:
        resp = httpx.get(f"{settings.admin_url.rstrip('/')}{path}", headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data: list[dict[str, Any]] = resp.json()
        return data
    except httpx.HTTPError as exc:
        logger.warning("배경 라이브러리 조회 실패(폴백): %s", exc)
        return []


def _match_terms(ticker: str) -> list[str]:
    """종목 → 매칭어(종목명·섹터). 태그와 겹치면 관련 배경."""
    name = stock_name(ticker)
    terms: list[str] = []
    if name:
        terms.append(name)
        sector = sector_of(name)
        if sector:
            terms.append(sector)
    return terms


def match_background(
    assets: list[dict[str, Any]], ticker: str
) -> LibraryBackground | None:
    """활성 자산 중 종목명·섹터 태그가 겹치고 파일이 실재하는 첫 배경. 없으면 None.

    순수 함수(테스트 용이) — 매칭은 태그 교집합, 파일 존재는 os.path.exists.
    """
    terms = {t for t in _match_terms(ticker)}
    if not terms:
        return None
    for a in assets:
        if not a.get("enabled", True):
            continue
        tags = {str(t) for t in a.get("tags", [])}
        if not (tags & terms):
            continue
        path = str(a.get("path", ""))
        if not path or not os.path.exists(path):
            continue  # 메타만 있고 파일 없음 → 다음 우선순위로
        return LibraryBackground(
            path=path, kind=str(a.get("kind", "image")),
            name=str(a.get("name", "")), license=str(a.get("license", "")),
        )
    return None


def select_library_background(ticker: str) -> LibraryBackground | None:
    """라이브러리에서 섹터/태그 매칭 배경 1개(auto·library 모드). 없으면 None(다음 폴백)."""
    return match_background(fetch_backgrounds(), ticker)
