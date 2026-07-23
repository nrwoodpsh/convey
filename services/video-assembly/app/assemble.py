"""ffmpeg 합성 — 차트 오버레이(+배경 broll·음성·연출) → 쇼츠 mp4. 라운드④·㉕·㉖.

정확한 차트·수치(render.py, 알파③)를 배경·음성과 합쳐 최종 mp4를 만든다.
㉖ 연출(단일 배경 + 오버레이): 수치 팝(fade) · 구간 자막(금색 강조·싱크) · 신뢰 배지 ·
인트로/아웃트로 전면 카드. 배경은 1개 유지(컷 전환 리스크 회피).
"""
from __future__ import annotations

import os
import subprocess

# 자막 한글 폰트(번들 NanumGothic) — render.py와 동일 파일. 없으면 drawtext 기본(tofu 위험).
_FONT = os.path.join(os.path.dirname(__file__), "assets", "NanumGothic.ttf")
_FONTFILE = f"fontfile={_FONT}:" if os.path.exists(_FONT) else ""
_GOLD = "#e9b44c"
_INTRO = 0.8
_OUTRO = 0.8

# 구간 자막 = (텍스트, 시작초, 끝초, 금색여부)
Caption = tuple[str, float, float, bool]


def _esc(s: str) -> str:
    """drawtext text 이스케이프 — 특수문자 제거/치환(개행은 유지 — 자막 줄바꿈용)."""
    return s.replace("\\", "").replace(":", r"\:").replace("'", "").replace("%", "")


def _shorten(s: str, n: int = 30) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _wrap(text: str, width: int = 18, max_lines: int = 2) -> str:
    """긴 자막 줄바꿈(㉗/P4) — 공백 우선, 없으면 글자 수. 초과분 말줄임. drawtext 실제 개행."""
    text = text.strip()
    lines: list[str] = []
    while text and len(lines) < max_lines:
        if len(text) <= width:
            lines.append(text)
            text = ""
            break
        cut = text.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        lines.append(text[:cut].strip())
        text = text[cut:].strip()
    if text and lines:  # 남은 초과분 → 마지막 줄 말줄임
        lines[-1] = (lines[-1][: width - 1] + "…") if len(lines[-1]) >= width else lines[-1] + "…"
    return "\n".join(lines)


def _drawtext(text: str, *, size: int, y: str, x: str = "(w-text_w)/2",
              alpha: float = 0.5, color: str = "white", enable: str = "") -> str:
    en = f":enable='{enable}'" if enable else ""
    return (
        f"drawtext={_FONTFILE}text='{_esc(text)}':fontcolor={color}:fontsize={size}:"
        f"box=1:boxcolor=black@{alpha}:boxborderw=10:x={x}:y={y}{en}"
    )


def build_bg_cuts(clips: list[str], out_mp4: str, *, duration: float, fps: int = 30) -> str | None:
    """N개 배경 영상 클립 → **하드 컷 전환** 배경 1개(㉙/D). 1080×1920·duration. 실패 시 None.

    각 클립을 스트림 루프+크롭+동일 길이 트림 후 concat(하드 컷). 클립 2개 미만이면 None(단일 폴백).
    (xfade는 stream_loop+trim 조합에서 -22 오류 → 견고한 concat 하드 컷 채택.)
    """
    n = len(clips)
    if n < 2:
        return None
    seg = max(duration / n, 1.0)  # 클립당 길이(균등 분배)
    inputs: list[str] = []
    for c in clips:
        inputs.extend(["-stream_loop", "-1", "-i", c])
    parts: list[str] = []
    for i in range(n):
        parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"setsar=1,fps={fps},trim=0:{seg:.2f},setpts=PTS-STARTPTS[c{i}]"
        )
    labels = "".join(f"[c{i}]" for i in range(n))
    parts.append(f"{labels}concat=n={n}:v=1:a=0[bg]")
    cmd = [
        "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts),
        "-map", "[bg]", "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-an", out_mp4,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, OSError):
        return None
    return out_mp4


def _run(
    *,
    bg_inputs: list[str],
    bg_filter: str,
    chart_png: str,
    out_mp4: str,
    duration: float,
    fps: int,
    audio_path: str | None,
    numbers_png: str | None = None,
    pop_start: float = 0.0,
    intro_png: str | None = None,
    outro_png: str | None = None,
    captions: list[Caption] | None = None,
    subtitle: str | None = None,
    badge: str | None = None,
) -> str:
    """공용 합성 — 배경 위에 차트·수치(팝)·자막·배지·인트로/아웃트로를 순서대로 오버레이."""
    inputs = list(bg_inputs)  # 입력0 = 배경
    idx = 1

    def add_img(path: str) -> int:
        nonlocal idx
        inputs.extend(["-loop", "1", "-i", path])
        idx += 1
        return idx - 1

    ci = add_img(chart_png)
    ni = add_img(numbers_png) if numbers_png else None
    ii = add_img(intro_png) if intro_png else None
    oi = add_img(outro_png) if outro_png else None
    if audio_path:
        inputs.extend(["-i", audio_path])
    else:  # 무음(합성 검증·자리표시)
        inputs.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
    ai = idx

    parts = [f"[0:v]{bg_filter}[bg]", f"[bg][{ci}:v]overlay=(W-w)/2:(H-h)/2[v]"]
    # 수치 팝 — chart 구간에 fade-in 등장
    if ni is not None:
        parts.append(f"[{ni}:v]fade=t=in:st={pop_start:.2f}:d=0.4:alpha=1[num]")
        parts.append(f"[v][num]overlay=(W-w)/2:(H-h)/2:enable='gte(t,{pop_start:.2f})'[v]")
    # 자막(구간 싱크·금색 강조) + 신뢰 배지 — 인트로/아웃트로보다 먼저(카드가 덮도록)
    draws: list[str] = []
    if captions:
        for text, start, end, gold in captions:
            draws.append(_drawtext(
                _wrap(text), size=44, y="h-280",
                color=_GOLD if gold else "white",
                enable=f"between(t,{start:.2f},{end:.2f})",
            ))
    elif subtitle:
        draws.append(_drawtext(_wrap(subtitle), size=48, y="h-280"))
    if badge:
        draws.append(_drawtext(_shorten(badge, 44), size=30, y="46", x="w-text_w-34", alpha=0.4))
    if draws:
        parts.append("[v]" + ",".join(draws) + "[v]")
    # 인트로/아웃트로 전면 카드(불투명) — enable 시간창으로 배경 위를 덮음
    if ii is not None:
        parts.append(f"[v][{ii}:v]overlay=0:0:enable='lt(t,{_INTRO})'[v]")
    if oi is not None:
        parts.append(f"[v][{oi}:v]overlay=0:0:enable='gt(t,{max(duration - _OUTRO, 0):.2f})'[v]")

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(parts),
        "-map", "[v]", "-map", f"{ai}:a",
        "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", "-shortest", out_mp4,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4


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
    numbers_png: str | None = None,
    pop_start: float = 0.0,
    intro_png: str | None = None,
    outro_png: str | None = None,
) -> str:
    """정지 이미지 → 쇼츠. 켄번즈(zoompan) 모션 + 오버레이 연출(㉖). 9:16."""
    frames = int(duration * fps)
    bg_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0004,1.15)':d={frames}:s=1080x1920:fps={fps},setsar=1"
    )
    return _run(
        bg_inputs=["-loop", "1", "-i", image_path], bg_filter=bg_filter,
        chart_png=chart_png, out_mp4=out_mp4, duration=duration, fps=fps,
        audio_path=audio_path, numbers_png=numbers_png, pop_start=pop_start,
        intro_png=intro_png, outro_png=outro_png,
        captions=captions, subtitle=subtitle, badge=badge,
    )


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
    numbers_png: str | None = None,
    pop_start: float = 0.0,
    intro_png: str | None = None,
    outro_png: str | None = None,
) -> str:
    """영상 배경(스톡 broll) → 쇼츠. 배경 9:16 크롭·반복 + 오버레이 연출(㉖). 투명 차트."""
    bg_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    return _run(
        bg_inputs=["-stream_loop", "-1", "-i", video_path], bg_filter=bg_filter,
        chart_png=chart_png, out_mp4=out_mp4, duration=duration, fps=fps,
        audio_path=audio_path, numbers_png=numbers_png, pop_start=pop_start,
        intro_png=intro_png, outro_png=outro_png,
        captions=captions, subtitle=subtitle, badge=badge,
    )
