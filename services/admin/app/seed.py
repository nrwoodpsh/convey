"""종목 마스터 시드(㉝ P1) — 최초 1회 stock 테이블 채움. 멱등(ticker upsert).

기본 source="static": common.stocks(현 46) 승격. "naver"(코스피200 스크래핑)는 후속.
사람/컨테이너 기동 시 실행(Dockerfile CMD). 이미 있으면 갱신만.
"""
from __future__ import annotations

import asyncio
import logging

from common.stocks import STOCK_NAMES, sector_of, stock_name
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.domains.admin.models import ScenarioTemplate, Stock

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


# 기본 시나리오 템플릿(㊳) — 기존 agent 하드코딩 3종을 admin_db로 이관(하위호환).
# id 고정(1속보·2분석·3스토리) — 대시보드 칩과 대본 생성 흐름이 이 id를 참조.
_SEED_TEMPLATES: tuple[dict[str, object], ...] = (
    {"id": 1, "name": "속보형", "description": "급등락 속보", "n_facts": 1, "n_relations": 1,
     "use_macro": False, "use_closing": False, "hook_tone": "속보 톤(급박하게)"},
    {"id": 2, "name": "분석형", "description": "담백한 분석", "n_facts": 3, "n_relations": 2,
     "use_macro": True, "use_closing": False, "hook_tone": "담백한 분석 톤"},
    {"id": 3, "name": "스토리형", "description": "이야기 도입", "n_facts": 2, "n_relations": 1,
     "use_macro": True, "use_closing": True, "hook_tone": "이야기를 여는 도입 톤"},
)


async def seed_templates() -> int:
    """기본 템플릿 3종 시드 — 멱등(id upsert). 정의는 갱신, enabled는 운영자 값 보존."""
    async with SessionLocal() as session:
        for row in _SEED_TEMPLATES:
            stmt = insert(ScenarioTemplate).values(**row, enabled=True)
            defn = {k: v for k, v in row.items() if k != "id"}  # enabled 제외 정의만
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=defn)
            await session.execute(stmt)
        # 명시적 id 시드는 SERIAL 시퀀스를 전진시키지 않음 → 신규 생성이 id=1과 충돌.
        # 시퀀스를 현재 최대 id 다음으로 보정(멱등).
        await session.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('scenario_template','id'), "
                "(SELECT MAX(id) FROM scenario_template))"
            )
        )
        await session.commit()
    logger.info("시나리오 템플릿 시드 완료: %d종", len(_SEED_TEMPLATES))
    return len(_SEED_TEMPLATES)


async def seed_all() -> None:
    # 한 이벤트루프에서 순차 실행 — asyncpg 엔진 풀이 단일 루프에 결속(루프 혼용 금지).
    await seed()
    await seed_templates()


def main() -> None:
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
