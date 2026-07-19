"""content 서비스 계층.

책임: 생성 잡 시작·단계 상태 관리, agent 스크립트 호출, 미디어 fan-out 발행,
      합성 완료 수신 → content.ready, 사람 승인 → content.approved,
      콘텐츠 히스토리 조회(중복회피 — 키워드/메타). TODO(/design): 흐름·상태머신 확정.
"""
from __future__ import annotations

from common.kafka import KafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content import repository
from app.domains.content.schemas import GenerateRequest, SearchResponse


async def start_generation(
    session: AsyncSession, producer: KafkaProducer, req: GenerateRequest, owner_id: str
) -> int:
    """생성 잡 시작. TODO(/builder): 잡 생성 → agent 스크립트 → 미디어 fan-out."""
    # TODO(/builder): GenerationJob 생성·커밋 후 후속 단계 트리거
    raise NotImplementedError("생성 파이프라인 미구현 — /builder")


async def search_history(session: AsyncSession, query: str, top_k: int) -> SearchResponse:
    """콘텐츠 히스토리 RAG 검색 — agent가 east-west 호출."""
    _ = repository  # 자리표시 (미구현)
    return SearchResponse(hits=[])
