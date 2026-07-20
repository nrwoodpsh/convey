"""ffmpeg 합성 — 차트 오버레이(+배경 broll·음성) → 쇼츠 mp4. 라운드④.

정확한 차트·수치(render.py, 알파③)를 배경·음성과 합쳐 최종 mp4를 만든다.
배경 broll·음성은 외부 API 산출(커모디티) — 여기선 로컬 ffmpeg 합성만.
"""
from __future__ import annotations

import subprocess


def compose(
    chart_png: str,
    out_mp4: str,
    *,
    duration: float = 5.0,
    background: str | None = None,
    audio: str | None = None,
) -> str:
    """차트 PNG를 9:16 쇼츠 mp4로 합성. 배경·음성 있으면 오버레이/믹스, 없으면 정지 차트."""
    cmd: list[str] = ["ffmpeg", "-y"]
    if background:
        cmd += ["-i", background, "-loop", "1", "-i", chart_png]
        filter_complex = "[0:v]scale=1080:1920[bg];[bg][1:v]overlay=(W-w)/2:(H-h)/2"
        cmd += ["-filter_complex", filter_complex, "-t", str(duration)]
    else:
        cmd += ["-loop", "1", "-i", chart_png, "-t", str(duration), "-vf", "scale=1080:1920"]
    if audio:
        cmd += ["-i", audio, "-shortest"]
    cmd += ["-pix_fmt", "yuv420p", out_mp4]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4
