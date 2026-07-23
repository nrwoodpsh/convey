"""근거 회수(RAG) — research의 /search를 east-west HTTP로 호출해 근거를 수집. 라운드⑤.

CONVEY의 RAG는 벡터 유사도가 아니라 **GraphRAG(관계·인과) + SQL 사실조회**다(ADR 0005·0006).
회수 로직은 research 내부(Neo4j Cypher + Postgres)이고, agent는 계약(/search)만 호출한다.
저장소 직접접근 금지 — 반드시 research API 경유(east-west + HMAC 서명).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from common.security import H_SIGNATURE, H_TIMESTAMP, H_USER_ID, sign_internal

from app.script.builder import (
    FactEvidence,
    MacroEvidence,
    PriceEvidence,
    RelationEvidence,
)


@dataclass
class Evidence:
    """스크립트 빌더 입력 — 가격(수치 슬롯) + 시계열(차트) + 사실(인용) + 거시 + **그래프 관계(인과)**."""

    price: PriceEvidence | None
    series: list[float] = field(default_factory=list)
    facts: list[FactEvidence] = field(default_factory=list)
    macros: list[MacroEvidence] = field(default_factory=list)
    relations: list[RelationEvidence] = field(default_factory=list)


class Retriever:
    def __init__(
        self, research_url: str, content_url: str, top_k: int, internal_secret: str
    ) -> None:
        self._research_url = research_url.rstrip("/")
        self._content_url = content_url.rstrip("/")
        self._top_k = top_k
        self._secret = internal_secret

    async def gather(
        self, topic: str, *, ticker: str | None = None, entity: str | None = None
    ) -> Evidence:
        """research /search 호출 → 가격 근거 + 사실. 저장소 직접접근 없음(계약만)."""
        path = "/research/search"
        params: dict[str, str | int] = {"q": topic, "top_k": self._top_k}
        if ticker:
            params["ticker"] = ticker
        if entity:
            params["entity"] = entity
        ts, sig = sign_internal(secret=self._secret, user_id="agent", path=path)
        headers = {H_USER_ID: "agent", H_TIMESTAMP: ts, H_SIGNATURE: sig}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self._research_url}{path}", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        price: PriceEvidence | None = None
        series: list[float] = []
        p = data.get("price")
        if p:
            price = {
                "ticker": str(p["ticker"]),
                "close": float(p["close"]),
                "change_pct": float(p["change_pct"]),
                "source_url": str(p["source_url"]),
                "ref_id": int(p["ref_id"]),
            }
            series = [float(x) for x in p.get("series", [])]
        facts: list[FactEvidence] = [
            {"text": str(f["text"]), "source_url": str(f["source_url"]), "ref_id": int(f["ref_id"])}
            for f in data.get("facts", [])
            if f.get("source_url")  # 가드레일: 무출처 제외
        ]
        macros: list[MacroEvidence] = [
            {
                "name": str(m["name"]), "value": float(m["value"]), "unit": str(m.get("unit", "")),
                "source_url": str(m["source_url"]), "ref_id": int(m["ref_id"]),
            }
            for m in data.get("macros", [])
            if m.get("source_url")  # 가드레일: 무출처 제외
        ]
        # 그래프 관계(인과) — 알파. /search가 주는 relations를 버리지 않고 스크립트로(㉕).
        relations: list[RelationEvidence] = [
            {
                "subject": str(r["subject"]), "edge": str(r["edge"]), "object": str(r["object"]),
                "source_url": str(r["source_url"]), "article_id": int(r["source_article_id"]),
            }
            for r in data.get("relations", [])
            if r.get("source_url")  # 가드레일: 무출처 관계 제외
        ]
        return Evidence(
            price=price, series=series, facts=facts, macros=macros, relations=relations
        )

    async def search(self, query: str) -> str:
        """/chat 에이전트 루프용 텍스트 컨텍스트 — 사실을 한 문자열로. (스크립트는 gather 사용)."""
        ev = await self.gather(query)
        return " / ".join(f["text"] for f in ev.facts)
