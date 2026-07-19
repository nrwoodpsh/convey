"""content 저장소 계층. TODO(/design): 잡·스크립트·자산 CRUD + 히스토리 조회."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def history_search(
    session: AsyncSession, query: str, top_k: int
) -> list[tuple[int, str]]:
    """콘텐츠 히스토리 중복회피용 조회 — 키워드/메타(주제·종목·기간) 매칭. 벡터 아님.

    TODO(/design): Content·Script 메타 대상 쿼리. 반환 (content_id, text).
    """
    raise NotImplementedError("히스토리 조회 미구현 — /builder")
