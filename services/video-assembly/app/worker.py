"""video-assembly 워커 — media.assemble 소비 → 정확 차트 + 로컬 배경 + ffmpeg 합성 → mp4. 라운드⑤.

핵심(알파③): 정확 차트·수치 렌더(render.py) + 합성(assemble.py). 키 없는 경로 —
배경=로컬 타이틀 카드, 오디오=무음(외부 broll/TTS 없음). 완료 시 content.assembled 회신(fan-in).
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import Any

from common.kafka import KafkaProducer, consume_forever
from common.logging import configure_logging
from common.stocks import stock_label

from app.assemble import build_short, build_short_video
from app.broll import PexelsClient
from app.config import settings
from app.render import ChartOverlay, render_chart, render_title_card
from app.tts import make_engine


def _audio_duration(path: str) -> float | None:
    """오디오 길이(초) — ffprobe. 실패 시 None."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            check=True, capture_output=True, text=True,
        )
        return float(out.stdout.strip())
    except (subprocess.CalledProcessError, OSError, ValueError):
        return None


_GAP = 0.35  # 구간 사이 무음(초) — 자연스러운 쉼


def _segment_audio(
    segments: list[dict[str, Any]], base: str,
) -> tuple[str | None, list[tuple[str, float, float]]]:
    """구간별 TTS(㉕/C3) → 무음 연결 오디오 + 구간 타이밍(자막 싱크용).

    하나라도 합성 실패(무음 엔진·오프라인)면 (None, []) → 호출측이 단일 내레이션으로 폴백.
    """
    engine = make_engine()
    parts: list[tuple[str, str, float]] = []  # (mp3, text, dur)
    for i, seg in enumerate(segments):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        mp3 = engine.synthesize(text, f"{base}-seg{i}")
        if not mp3:
            return None, []
        parts.append((mp3, text, _audio_duration(mp3) or 0.0))
    if len(parts) < 2:
        return None, []
    try:
        sil = f"{base}-sil.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", str(_GAP), "-c:a", "libmp3lame", sil],
            check=True, capture_output=True,
        )
        listfile = f"{base}-concat.txt"
        lines: list[str] = []
        for i, (mp3, _t, _d) in enumerate(parts):
            lines.append(f"file '{mp3}'")
            if i < len(parts) - 1:
                lines.append(f"file '{sil}'")
        with open(listfile, "w") as f:
            f.write("\n".join(lines))
        out = f"{base}-tts.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
             "-c:a", "libmp3lame", out],
            check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None, []
    caps: list[tuple[str, float, float]] = []
    t = 0.0
    for (_mp3, text, dur) in parts:
        caps.append((text, t, t + dur))
        t += dur + _GAP
    return out, caps

configure_logging(settings.log_level)
logger = logging.getLogger("video-assembly")


async def handle_assemble(event: dict[str, Any], producer: KafkaProducer) -> None:
    """media.assemble 1건 → 차트 PNG + 배경 카드 + 쇼츠 mp4 → content.assembled 발행."""
    job_id = int(event["job_id"])
    chart = event["chart"]
    title = str(event.get("title", ""))
    subtitle = str(event.get("subtitle", ""))
    narration = str(event.get("narration", "")) or subtitle
    broll_query = str(event.get("broll_query", "")) or title
    duration = float(event.get("duration", 6.0))
    segments = event.get("segments") or []  # 구간 자막·음성(㉕/C)
    trust = event.get("trust") or {}
    badge = (
        f"출처 {trust['source_host']} · {trust['published_date']}"
        if trust.get("source_host") else None
    )

    os.makedirs(settings.media_dir, exist_ok=True)
    base = os.path.join(settings.media_dir, f"job-{job_id}")
    chart_png, bg_png, out_mp4 = f"{base}-chart.png", f"{base}-bg.png", f"{base}.mp4"

    broll_meta: dict[str, str] = {}
    try:
        overlay = ChartOverlay(
            ticker=str(chart["ticker"]),
            close=float(chart["close"]),
            change_pct=float(chart["change_pct"]),
            series=[float(x) for x in chart.get("series", [])],
            title=title,  # 최상단 제목(주제)
            stock_label=stock_label(str(chart["ticker"])),  # '현대차(005380)' — 코드만 X
        )
        await asyncio.to_thread(render_chart, overlay, chart_png)  # 투명 오버레이
        # 구간 TTS(㉕/C) — 구간별 합성→싱크 자막. 실패 시 단일 내레이션 폴백.
        captions: list[tuple[str, float, float]] = []
        audio_path: str | None = None
        if segments:
            audio_path, captions = await asyncio.to_thread(_segment_audio, segments, base)
        if audio_path is None:  # 폴백: 단일 내레이션(구간 자막 없음)
            audio_path = await asyncio.to_thread(make_engine().synthesize, narration, f"{base}-tts")
            captions = []
        if audio_path:
            audio_dur = _audio_duration(audio_path)
            if audio_dur:
                duration = audio_dur
        # 쇼츠 목표 길이(㉑): 음성이 짧아도 최소 확보, 1분 이내 상한. 짧으면 배경 지속.
        duration = min(max(duration, settings.min_duration), settings.max_duration)
        # broll 배경(Pexels) — video/photo, 실패 시 로컬 카드 폴백
        broll = await asyncio.to_thread(
            PexelsClient(settings.pexels_api_key).fetch,
            broll_query, f"{base}-broll", settings.broll_mode,
        )
        if broll is not None:
            broll_meta = {
                "broll_source_url": broll.source_url,
                "broll_author": broll.author,
                "broll_license": broll.license,
            }
            if broll.kind == "video":
                await asyncio.to_thread(
                    build_short_video, broll.path, chart_png, out_mp4,
                    duration=duration, audio_path=audio_path, subtitle=subtitle,
                    captions=captions or None, badge=badge,
                )
            else:  # photo → 켄번즈
                await asyncio.to_thread(
                    build_short, broll.path, chart_png, out_mp4,
                    duration=duration, audio_path=audio_path, subtitle=subtitle,
                    captions=captions or None, badge=badge,
                )
        else:  # 폴백: 로컬 타이틀 카드(현행)
            await asyncio.to_thread(render_title_card, title, bg_png)
            await asyncio.to_thread(
                build_short, bg_png, chart_png, out_mp4,
                duration=duration, audio_path=audio_path, subtitle=subtitle,
                captions=captions or None, badge=badge,
            )
    except Exception as exc:  # noqa: BLE001 — 실패도 회신(잡을 failed로)
        await producer.publish(
            settings.topic_assembled,
            {"job_id": job_id, "ok": False, "error": str(exc)[:300]},
            key=str(job_id),
        )
        logger.exception("합성 실패 job=%s", job_id)
        return

    await producer.publish(
        settings.topic_assembled,
        {"job_id": job_id, "ok": True, "mp4_path": out_mp4, **broll_meta},
        key=str(job_id),
    )
    logger.info("합성 완료 job=%s mp4=%s broll=%s", job_id, out_mp4, broll_meta.get("broll_source_url", "로컬카드"))


async def run() -> None:
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info("video-assembly 시작 — media.assemble 대기 (render → compose → content.assembled)")

    async def handler(event: dict[str, Any]) -> None:
        await handle_assemble(event, producer)

    try:
        await consume_forever(
            topic=settings.topic_assemble,
            group_id=settings.consumer_group,
            bootstrap=settings.kafka_bootstrap,
            handler=handler,
        )
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
