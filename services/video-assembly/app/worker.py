"""video-assembly 워커 — media.assemble 소비 → 정확 차트 + 로컬 배경 + ffmpeg 합성 → mp4. 라운드⑤.

핵심(알파③): 정확 차트·수치 렌더(render.py) + 합성(assemble.py). 키 없는 경로 —
배경=로컬 타이틀 카드, 오디오=무음(외부 broll/TTS 없음). 완료 시 content.assembled 회신(fan-in).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from common.kafka import KafkaProducer, consume_forever
from common.logging import configure_logging

from app.assemble import build_short
from app.config import settings
from app.render import ChartOverlay, render_chart, render_title_card

configure_logging(settings.log_level)
logger = logging.getLogger("video-assembly")


async def handle_assemble(event: dict[str, Any], producer: KafkaProducer) -> None:
    """media.assemble 1건 → 차트 PNG + 배경 카드 + 쇼츠 mp4 → content.assembled 발행."""
    job_id = int(event["job_id"])
    chart = event["chart"]
    title = str(event.get("title", ""))
    subtitle = str(event.get("subtitle", ""))
    duration = float(event.get("duration", 6.0))

    os.makedirs(settings.media_dir, exist_ok=True)
    base = os.path.join(settings.media_dir, f"job-{job_id}")
    chart_png, bg_png, out_mp4 = f"{base}-chart.png", f"{base}-bg.png", f"{base}.mp4"

    try:
        overlay = ChartOverlay(
            ticker=str(chart["ticker"]),
            close=float(chart["close"]),
            change_pct=float(chart["change_pct"]),
            series=[float(x) for x in chart.get("series", [])],
        )
        await asyncio.to_thread(render_chart, overlay, chart_png)
        await asyncio.to_thread(render_title_card, title, bg_png)
        await asyncio.to_thread(
            build_short, bg_png, chart_png, out_mp4, duration=duration, subtitle=subtitle
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
        {"job_id": job_id, "ok": True, "mp4_path": out_mp4},
        key=str(job_id),
    )
    logger.info("합성 완료 job=%s mp4=%s", job_id, out_mp4)


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
