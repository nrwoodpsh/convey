"""외부 시세 연동 워커 — 주기적으로 KRX 시세를 받아 Kafka로 발행.

배포 형태 ②(워커/데몬): HTTP 서버 아님, 게이트웨이 뒤 아님. 다른 서비스는
Kafka 토픽(market.ticks)을 구독해 시세를 소비한다(이벤트 주도).
소스는 pykrx(무료·키X) — KRX 일봉 최신 거래일 실측(ADR 0008).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from common.kafka import KafkaProducer
from common.logging import configure_logging

from app.config import settings
from app.external_client import KrxMarketClient

configure_logging(settings.log_level)
logger = logging.getLogger("market-feed")


async def run() -> None:
    symbols = [s.strip() for s in settings.symbols.split(",") if s.strip()]
    client = KrxMarketClient(settings.lookback_days)
    producer = KafkaProducer(settings.kafka_bootstrap)
    await producer.start()
    logger.info(
        "market-feed 시작 symbols=%s interval=%ss", symbols, settings.poll_interval_seconds
    )
    try:
        while True:
            today = datetime.now(timezone.utc).date()
            for symbol in symbols:
                tick = await asyncio.to_thread(client.latest_ohlcv, symbol, today)
                if tick is None:
                    continue  # 데이터 없으면 스킵 (가드레일: 추정값 발행 금지)
                await producer.publish(settings.topic_ticks, tick, key=symbol)
                logger.info("tick ticker=%s close=%s ts=%s", symbol, tick["close"], tick["ts"])
            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        await producer.stop()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
