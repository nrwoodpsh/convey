"""YouTube 발행 부패방지 검증(㊶ C1) — 출처·면책 description·키 게이팅·미연결 skip."""
from __future__ import annotations

import asyncio

import pytest

from app.youtube import YouTubeClient, build_description


def test_description_carries_disclaimer_and_sources() -> None:
    d = build_description("삼성전자 급등", ["https://n/1", "https://n/1", "https://k/2"])
    assert "삼성전자 급등" in d
    assert "투자 권유가 아닙니다" in d          # 면책 계승(가드레일)
    assert "https://n/1" in d and "https://k/2" in d
    assert d.count("https://n/1") == 1          # 출처 중복 제거


def test_description_without_sources() -> None:
    d = build_description("제목만")
    assert "제목만" in d and "출처:" not in d


def test_not_configured_without_creds() -> None:
    assert YouTubeClient().configured is False
    assert YouTubeClient(client_id="a", client_secret="b").configured is False  # refresh 없음
    assert YouTubeClient(client_id="a", client_secret="b", refresh_token="c").configured is True


def test_upload_skips_without_creds() -> None:
    """자격증명 없으면 업로드 시도 없이 NotImplementedError(미연결) — consumer가 failed 기록."""
    with pytest.raises(NotImplementedError):
        asyncio.run(YouTubeClient().upload("/tmp/x.mp4", title="t"))
