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
        # 로컬 TTS(무료) — 없으면 무음. 음성 있으면 영상 길이를 음성에 맞춤.
        audio_path = await asyncio.to_thread(make_engine().synthesize, narration, f"{base}-tts")
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
                )
            else:  # photo → 켄번즈
                await asyncio.to_thread(
                    build_short, broll.path, chart_png, out_mp4,
                    duration=duration, audio_path=audio_path, subtitle=subtitle,
                )
        else:  # 폴백: 로컬 타이틀 카드(현행)
            await asyncio.to_thread(render_title_card, title, bg_png)
            await asyncio.to_thread(
                build_short, bg_png, chart_png, out_mp4,
                duration=duration, audio_path=audio_path, subtitle=subtitle,
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
