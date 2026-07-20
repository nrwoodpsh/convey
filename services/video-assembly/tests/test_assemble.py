"""build_short 검증(알파③) — 이미지만으로 9:16 쇼츠 mp4(켄번즈+차트+오디오)."""
from __future__ import annotations

import os
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.assemble import build_short  # noqa: E402
from app.render import ChartOverlay, render_chart  # noqa: E402


def test_build_short_produces_9x16_mp4() -> None:
    with tempfile.TemporaryDirectory() as d:
        # 배경 이미지(broll 자리표시)
        fig, ax = plt.subplots(figsize=(9, 16), dpi=40)
        ax.axis("off")
        bg = os.path.join(d, "bg.png")
        fig.savefig(bg)
        plt.close(fig)
        chart = render_chart(ChartOverlay("005930", 71900, 2.34, [70000, 71900]), os.path.join(d, "c.png"))
        out = build_short(bg, chart, os.path.join(d, "s.mp4"), duration=2, subtitle="005930 +2.34%")
        assert os.path.getsize(out) > 5000
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name", "-of", "csv=p=0", out],
            capture_output=True, text=True,
        )
        out_probe = probe.stdout  # ffprobe 필드 순서: codec_name,width,height
        assert "h264" in out_probe and "1080" in out_probe and "1920" in out_probe  # 9:16 세로 h264
