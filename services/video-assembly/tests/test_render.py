"""정확 렌더 검증(알파③) — 수치 포맷이 입력값을 그대로(환각 0) + 실제 PNG 산출."""
from __future__ import annotations

import os
import tempfile

from app.render import ChartOverlay, format_price, render_chart


def test_format_price_exact() -> None:
    # 입력 수치를 그대로(자리수·부호만) — 값 변형 없음
    assert format_price(71900, 2.34) == ("71,900원", "+2.34%")
    assert format_price(50000, -3.1) == ("50,000원", "-3.10%")


def test_render_produces_png() -> None:
    overlay = ChartOverlay(ticker="005930", close=71900, change_pct=2.34, series=[70000, 71000, 71900])
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "chart.png")
        path = render_chart(overlay, out)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000  # 실제 이미지 산출(빈 파일 아님)
        with open(path, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"  # PNG 시그니처
