"""생성 배경 래퍼 검증(㊴ P2) — 프롬프트 부패방지(원문 미전달) + 키 게이팅 폴백."""
from __future__ import annotations

from app.imagegen import ImageGenClient, build_prompt


def test_prompt_uses_sector_only() -> None:
    """현대차(섹터=자동차) 프롬프트는 섹터·무드·스타일만 — 종목명·원문 텍스트 없음(가드레일)."""
    p = build_prompt("005380")
    assert "자동차" in p or "도로" in p  # 섹터 무드 반영
    assert "귀엽" in p and "9:16" in p    # 스타일·구도
    assert "현대차" not in p              # 종목명 미포함(원문 미전달)


def test_prompt_unknown_sector_defaults() -> None:
    """사전 밖·미상 종목도 심플 기본으로 생성(빈 프롬프트 아님)."""
    p = build_prompt("999999")
    assert p and "심플" in p


def test_no_key_skips() -> None:
    """키 없으면 generate가 항상 None(skip) → 워커가 Pexels로 폴백."""
    client = ImageGenClient(api_key="", api_url="https://x/v1", model="m")
    assert client.generate("005380", "/tmp/x.png") is None


def test_call_api_no_key_none() -> None:
    """_call_api도 키·URL 없으면 외부 호출 없이 None(부패방지 경계)."""
    assert ImageGenClient(api_key="", api_url="", model="m")._call_api("p") is None
