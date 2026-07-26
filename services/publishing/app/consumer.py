"""publishing 소비 — content.approved → 발행 큐잉 + YouTube 업로드. 라운드⑤·㊶ (알파4).

멱등 상태머신(service) + YouTube 부패방지(youtube)가 핵심. 발행은 **사람 승인(content.approved) 후에만**.
㊶: 이벤트가 mp4 경로·제목·출처를 실어 오면 그대로 업로드(출처·면책 description·기본 private).
이미 published면 재업로드 안 함(멱등). 자격증명 없으면 failed로 기록(재시도 가능).
"""
from __future__ import annotations

import logging
import os
from typing import Any

from common.kafka import consume_forever

from app import service
from app.config import settings
from app.db import SessionLocal
from app.schemas import PublishStatus
from app.youtube import YouTubeClient, build_description

logger = logging.getLogger("publishing.consumer")


def _resolve_mp4(event: dict[str, Any]) -> str:
    """이벤트 mp4_path 우선, 없으면 공유 볼륨 관례 경로(job-{job_id}.mp4) 폴백."""
    p = str(event.get("mp4_path", "") or "")
    if p:
        return p
    return os.path.join(settings.media_dir, f"job-{event.get('job_id')}.mp4")


async def run_consumer() -> None:
    yt = YouTubeClient(
        client_id=settings.youtube_client_id,
        client_secret=settings.youtube_client_secret,
        refresh_token=settings.youtube_refresh_token,
        token_uri=settings.youtube_token_uri,
        privacy=settings.youtube_privacy,
    )

    async def handler(event: dict[str, Any]) -> None:
        content_id = event.get("content_id")
        if content_id is None:
            logger.warning("content.approved에 content_id 없음: %s", event)
            return
        cid = int(content_id)
        async with SessionLocal() as session:
            rec = await service.enqueue(session, cid)  # 멱등 큐잉
            if rec.status == PublishStatus.PUBLISHED.value:
                logger.info("이미 발행됨 content=%s — 재업로드 skip(멱등)", cid)
                return
            title = str(event.get("title", "") or f"CONVEY 쇼츠 #{cid}")
            desc = build_description(title, event.get("sources") or [])  # 출처·면책 계승
            try:
                url = await yt.upload(
                    _resolve_mp4(event), title=title, description=desc, tags=["주식", "쇼츠"]
                )
                await service.mark_published(session, cid, url)
                logger.info("발행 완료 content=%s url=%s", cid, url)
            except NotImplementedError as exc:  # 자격증명·연결 전 — 실패로 기록(재시도 가능)
                await service.mark_failed(session, cid, str(exc))
            except Exception as exc:  # noqa: BLE001 — 업로드 실패도 기록(재시도), 파이프라인 보호
                await service.mark_failed(session, cid, str(exc)[:400])
                logger.exception("발행 실패 content=%s", cid)

    await consume_forever(
        topic=settings.topic_approved,
        group_id=settings.consumer_group,
        bootstrap=settings.kafka_bootstrap,
        handler=handler,
    )
