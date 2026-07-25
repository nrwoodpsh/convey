"""생성 배경(㊴ P2) — 외부 이미지 생성 API 래퍼(부패방지 계층). 귀여운/심플 배경 → 켄번즈.

가드레일:
  - 미디어 생성은 외부 API 허용하되 **원문 텍스트 미전달** — 프롬프트는 섹터·무드·스타일만.
  - 키 없으면 skip(None) → 워커가 다음 우선순위(Pexels)로 폴백(파이프라인 보호).
  - 생성물은 license="generated"로 소스 메타 기록(출처 계승 가드레일).

구조는 broll.py(PexelsClient)·tts.py와 동일한 in-process 래퍼 — 워커 우선순위 체인에서 동기 호출.
외부 호출은 `_call_api` 한 곳에 격리(OpenAI images 호환 형태) — 공급자 교체 시 이 메서드만 변경.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx
from common.stocks import sector_of, stock_name

from app.config import settings

logger = logging.getLogger("video-assembly")

# 섹터 → 무드 문구(프롬프트 재료). 사전 밖은 심플 기본. 원문 텍스트는 절대 넣지 않음(가드레일).
_SECTOR_MOOD: dict[str, str] = {
    "자동차": "도로와 자동차",
    "반도체": "반도체 칩과 회로",
    "2차전지": "배터리와 전기",
    "바이오": "연구실과 분자",
    "인터넷": "네트워크와 화면",
    "금융": "동전과 그래프",
    "엔터": "무대와 조명",
    "조선": "바다와 배",
    "철강": "공장과 금속",
}


@dataclass
class GeneratedBackground:
    """생성된 배경 이미지 + 생성 소스·라이선스 메타."""

    path: str
    prompt: str
    source: str            # 생성 provider(모델)
    kind: str = "image"
    license: str = "generated"  # 생성물(외부 API 산출) — 상세 약관은 provider 계정 귀속


def build_prompt(ticker: str) -> str:
    """섹터·무드 + '귀여운/심플' 스타일 프롬프트. 원문 텍스트 미전달(가드레일)."""
    name = stock_name(ticker)
    sector = sector_of(name) if name else None
    mood = _SECTOR_MOOD.get(sector or "", "심플한 도형")
    return (
        f"{mood} 모티프의 귀엽고 심플한 미니멀 플랫 일러스트 배경, "
        "파스텔 톤, 세로 9:16 구도, 글자·로고·워터마크 없음"
    )


class ImageGenClient:
    """외부 이미지 생성 API 래퍼 — 키 없으면 항상 None(skip). 외부 호출은 `_call_api`에 격리."""

    def __init__(self, api_key: str = "", api_url: str = "", model: str = "") -> None:
        self._key = api_key
        self._url = api_url.rstrip("/")
        self._model = model

    def _call_api(self, prompt: str) -> bytes | None:
        """이미지 1장 생성 → PNG 바이트. OpenAI images 호환(b64_json). 실패·키없음 시 None."""
        if not self._key or not self._url:
            return None
        try:
            resp = httpx.post(
                f"{self._url}/images/generations",
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self._model, "prompt": prompt,
                    "size": "1024x1792", "response_format": "b64_json", "n": 1,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            b64 = (data.get("data") or [{}])[0].get("b64_json")
            return base64.b64decode(b64) if b64 else None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("이미지 생성 실패 → 폴백: %s", exc)
            return None

    def generate(self, ticker: str, out_path: str) -> GeneratedBackground | None:
        """섹터·무드 프롬프트로 배경 1장 생성. 키 없거나 실패면 None(폴백)."""
        if not self._key:
            return None  # skip(설계: 키 없으면 생성 단계 건너뜀)
        prompt = build_prompt(ticker)
        png = self._call_api(prompt)
        if not png:
            return None
        path = out_path if out_path.endswith(".png") else f"{out_path}.png"
        try:
            with open(path, "wb") as f:
                f.write(png)
        except OSError as exc:
            logger.warning("생성 이미지 저장 실패 → 폴백: %s", exc)
            return None
        return GeneratedBackground(path=path, prompt=prompt, source=self._model or "image-gen")


def make_client() -> ImageGenClient:
    """설정 기반 클라이언트 — 키 미설정이면 generate가 항상 None(폴백)."""
    return ImageGenClient(
        api_key=settings.image_gen_api_key,
        api_url=settings.image_gen_api_url,
        model=settings.image_gen_model,
    )
