"""종목 마스터 시드(㉝ P1) — 최초 1회 stock 테이블 채움. 멱등(ticker upsert).

기본 source="static": common.stocks(현 46) 승격. "naver"(코스피200 스크래핑)는 후속.
사람/컨테이너 기동 시 실행(Dockerfile CMD). 이미 있으면 갱신만.
"""
from __future__ import annotations

import asyncio
import logging

from common.stocks import STOCK_NAMES, sector_of, stock_name
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.domains.admin.models import Stock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("admin.seed")


def _static_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ticker in STOCK_NAMES:
        name = stock_name(ticker) or ""
        rows.append({"ticker": ticker, "name": name, "sector": sector_of(name) or ""})
    return rows


async def seed(source: str = "") -> int:
    src = source or settings.seed_source
    if src != "static":
        logger.warning("seed_source=%s 미구현 — static(common.stocks)으로 진행(후속)", src)
    rows = _static_rows()
    async with SessionLocal() as session:
        for r in rows:
            stmt = insert(Stock).values(**r, enabled=True)
            # 멱등: 존재 시 name·sector만 갱신(enabled는 운영자 값 보존)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker"], set_={"name": r["name"], "sector": r["sector"]}
            )
            await session.execute(stmt)
        await session.commit()
    logger.info("종목 시드 완료: %d행 (source=%s)", len(rows), src)
    return len(rows)


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
