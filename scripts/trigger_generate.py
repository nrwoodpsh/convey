"""쇼츠 1건 생성 트리거 — issue.selected 발행 → content 자동 양산 → ready까지 폴링.

스택이 떠 있어야 함(scripts/up.sh). 호스트에서 Kafka(29092)·PG(5432)로 접속.
성공 시 마지막 줄에 `MP4=/data/media/job-<id>.mp4`(컨테이너 경로)와 `JOB=<id>` 출력.
사용: python scripts/trigger_generate.py <ticker>   (기본 005930)
"""
from __future__ import annotations

import asyncio
import json
import sys
import time

import asyncpg
from aiokafka import AIOKafkaProducer

KAFKA = "localhost:29092"
PG = "postgresql://app:app@localhost:5432/content_db"


async def main() -> int:
    ticker = sys.argv[1] if len(sys.argv) > 1 else "005930"
    # 1) issue.selected 발행 → content.handle_issue → start_generation(자동)
    prod = AIOKafkaProducer(bootstrap_servers=KAFKA, value_serializer=lambda v: json.dumps(v).encode())
    await prod.start()
    try:
        await prod.send_and_wait(
            "issue.selected",
            {"ticker": ticker, "name": "", "score": 9.9, "as_of": "2026-07-22T00:00:00+00:00"},
            key=ticker.encode(),
        )
        print(f"[trigger] issue.selected 발행 ticker={ticker} → 자동 생성 시작")
    finally:
        await prod.stop()

    # 2) ready 폴링 (스크립트 생성=Ollama + 합성=ffmpeg + broll 다운로드 포함, ~2분 여유)
    conn = await asyncpg.connect(PG)
    try:
        deadline = time.time() + 240
        job_id = None
        while time.time() < deadline:
            row = await conn.fetchrow(
                "SELECT id, status, content_id FROM generation_jobs "
                "WHERE ticker=$1 AND owner_id='auto' ORDER BY id DESC LIMIT 1",
                ticker,
            )
            if row:
                job_id = row["id"]
                if row["status"] == "ready" and row["content_id"]:
                    c = await conn.fetchrow(
                        "SELECT mp4_path FROM contents WHERE id=$1", row["content_id"]
                    )
                    print(f"[trigger] ✓ ready  JOB={job_id}")
                    print(f"MP4={c['mp4_path']}")
                    print(f"JOB={job_id}")
                    return 0
                if row["status"] == "failed":
                    print(f"[trigger] ✗ 실패 JOB={job_id}")
                    return 2
                print(f"[trigger] ... job={job_id} status={row['status']}")
            await asyncio.sleep(4)
        print(f"[trigger] ✗ 타임아웃(job={job_id})")
        return 3
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
