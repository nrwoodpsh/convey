"""외부 시세 연동 워커 — 주기적으로 외부에서 시세를 받아 Kafka로 발행.

배포 형태 ②(워커/데몬): HTTP 서버 아님, 게이트웨이 뒤 아님. 다른 서비스는
Kafka 토픽(market.ticks)을 구독해 시세를 소비한다(이벤트 주도).
"""
from __future__ import annotations

import asyncio
import logging

from common.kafka import KafkaProducer
from common.logging import configure_logging

from app.config import settings
from app.external_client import ExternalMarketClient

configure_logging(settings.log_level)
logger = logging.getLogger("market-feed")


async def run() -> None:
    symbols = [s.strip() for s in settings.symbols.split(",") if s.strip()]
    client = ExternalMarketClient(
        settings.external_base_url, settings.kis_app_key, settings.kis_app_secret
    )
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info(
        "market-feed 시작 symbols=%s interval=%ss", symbols, settings.poll_interval_seconds
    )
    try:
        while True:
            for symbol in symbols:
                tick = await client.fetch_tick(symbol)
                await producer.publish(settings.topic_ticks, tick, key=symbol)
            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
