"""Kafka 학습잡 소비 워커 — llm-inference의 /train이 발행한 잡을 처리."""
from __future__ import annotations

import asyncio
import logging

from common.kafka import consume_forever
from common.logging import configure_logging

from app.config import settings

configure_logging(settings.log_level)
logger = logging.getLogger("trainer")


async def handle(job: dict) -> None:
    if job.get("type") != "lora.train.requested":
        logger.warning("무시: 알 수 없는 잡 타입 %s", job.get("type"))
        return
    logger.info("학습잡 수신: %s", job)

    # 무거운 임포트/연산은 워커 스레드에서 (이벤트 루프 블로킹 방지)
    from app.ollama_export import write_modelfile
    from app.trainer import run_lora_training

    out_dir = await asyncio.to_thread(run_lora_training, job, settings.adapters_dir)
    await asyncio.to_thread(write_modelfile, out_dir, job["base_model"])
    logger.info("학습잡 완료: %s", out_dir)


def main() -> None:
    asyncio.run(
        consume_forever(
            topic=settings.topic_train_jobs,
            group_id=settings.consumer_group,
            bootstrap=settings.kafka_bootstrap,
            handler=handle,
        )
    )


if __name__ == "__main__":
    main()
