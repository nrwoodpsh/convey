"""ffmpeg 합성 — 차트 오버레이(+배경 broll·음성) → 쇼츠 mp4. 라운드④.

정확한 차트·수치(render.py, 알파③)를 배경·음성과 합쳐 최종 mp4를 만든다.
배경 broll·음성은 외부 API 산출(커모디티) — 여기선 로컬 ffmpeg 합성만.
"""
from __future__ import annotations

import os
import subprocess

# 자막 한글 폰트(번들 NanumGothic) — render.py와 동일 파일. 없으면 drawtext 기본(tofu 위험).
_FONT = os.path.join(os.path.dirname(__file__), "assets", "NanumGothic.ttf")
_FONTFILE = f"fontfile={_FONT}:" if os.path.exists(_FONT) else ""

# 구간 자막 = (텍스트, 시작초, 끝초)
Caption = tuple[str, float, float]


def _esc(s: str) -> str:
    """drawtext text 이스케이프 — 특수문자 제거/치환(필터 파서 보호)."""
    return s.replace("\\", "").replace(":", r"\:").replace("'", "").replace("%", "").replace("\n", " ")


def _shorten(s: str, n: int = 30) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _drawtext(text: str, *, size: int, y: str, x: str = "(w-text_w)/2",
              alpha: float = 0.5, enable: str = "") -> str:
    en = f":enable='{enable}'" if enable else ""
    return (
        f"drawtext={_FONTFILE}text='{_esc(text)}':fontcolor=white:fontsize={size}:"
        f"box=1:boxcolor=black@{alpha}:boxborderw=10:x={x}:y={y}{en}"
    )


def _text_layer(
    captions: list[Caption] | None, subtitle: str | None, badge: str | None
) -> str:
    """자막(구간 싱크 or 단일 폴백) + 신뢰 배지 → drawtext 체인. 없으면 빈 문자열."""
    draws: list[str] = []
    if captions:
        for text, start, end in captions:
            draws.append(_drawtext(
                _shorten(text), size=44, y="h-240",
                enable=f"between(t,{start:.2f},{end:.2f})",
            ))
    elif subtitle:
        draws.append(_drawtext(_shorten(subtitle, 40), size=48, y="h-240"))
    if badge:
        # 신뢰 배지 — 우상단, 작게·상시(정확 데이터 알파 체감)
        draws.append(_drawtext(
            _shorten(badge, 34), size=30, y="46", x="w-text_w-34", alpha=0.4,
        ))
    if not draws:
        return ""
    return ";[v]" + ",".join(draws) + "[v]"


def build_short(
    image_path: str,
    chart_png: str,
    out_mp4: str,
    *,
    duration: float = 5.0,
    fps: int = 30,
    audio_path: str | None = None,
    subtitle: str | None = None,
    captions: list[Caption] | None = None,
    badge: str | None = None,
) -> str:
    """정지 이미지 → 쇼츠 영상. 켄번즈(zoompan) 모션 + 차트 오버레이 + (구간 자막·배지) + 오디오. 9:16.

    생성형 영상 없이 이미지만으로 영상을 만든다(ADR 0006). 수치·차트는 chart_png(정확 렌더).
    """
    frames = int(duration * fps)
    vf = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0004,1.15)':d={frames}:s=1080x1920:fps={fps},setsar=1[bg];"
        "[bg][1:v]overlay=(W-w)/2:(H-h)/2[v]"
    )
    vf += _text_layer(captions, subtitle, badge)
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-loop", "1", "-i", chart_png]
    if audio_path:
        cmd += ["-i", audio_path]
    else:  # 음성 없으면 무음 트랙(합성 검증·자리표시)
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += [
        "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
        "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", "-shortest", out_mp4,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4


def build_short_video(
    video_path: str,
    chart_png: str,
    out_mp4: str,
    *,
    duration: float = 6.0,
    fps: int = 30,
    audio_path: str | None = None,
    subtitle: str | None = None,
    captions: list[Caption] | None = None,
    badge: str | None = None,
) -> str:
    """영상 배경(스톡 broll) → 쇼츠. 배경 9:16 크롭·반복 + 차트 오버레이 + (구간 자막·배지) + 오디오.

    켄번즈 대신 배경 자체 모션 사용(B-2). chart_png는 투명 1080×1920(배경 노출).
    """
    vf = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];"
        "[bg][1:v]overlay=(W-w)/2:(H-h)/2[v]"
    )
    vf += _text_layer(captions, subtitle, badge)
    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", video_path, "-loop", "1", "-i", chart_png]
    if audio_path:
        cmd += ["-i", audio_path]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += [
        "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
        "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", "-shortest", out_mp4,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4


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
