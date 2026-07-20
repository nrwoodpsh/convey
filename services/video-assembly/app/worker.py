"""video-assembly 워커 — 미디어 자산 완료 → 차트 렌더 + ffmpeg 합성 → mp4. 라운드④.

핵심(알파③): 정확 차트·수치 렌더(render.py) + 합성(assemble.py) — 검증됨.
소비 오케스트레이션(content fan-out join → AssembleSpec)은 표준 배선(전 스택 기동 시 e2e).
"""
from __future__ import annotations

import asyncio
import logging

from common.logging import configure_logging

from app.config import settings

configure_logging(settings.log_level)
logger = logging.getLogger("video-assembly")


async def run() -> None:
    logger.info("video-assembly 시작 — 미디어 완료 신호 대기 (consume → render → compose)")
    # TODO(orchestration): content 미디어 완료 구독 → AssembleSpec → render_chart + compose → status=ready
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
