"""Neo4j 그래프 리포지토리 — 노드/엣지 upsert + traversal 회수. 라운드① (ADR 0005).

관계는 반드시 근거 기사(source_article_id)에 결속(환각 방지·감사). 엣지 타입은
허용 목록(EDGE_TYPES)만 — 동적 타입은 화이트리스트 검증 후에만 Cypher에 넣어 주입을 막는다.
"""
from __future__ import annotations

from typing import Any

from app.extract.relations import EDGE_TYPES


class GraphRepo:
    def __init__(self, driver: Any) -> None:
        self._driver = driver

    def upsert_relation(
        self, subject: str, edge: str, obj: str, *, source_article_id: int
    ) -> None:
        if edge not in EDGE_TYPES:  # 화이트리스트 — 주입·오타 차단
            raise ValueError(f"허용되지 않은 엣지: {edge}")
        query = (
            "MERGE (s:Entity {name: $s}) "
            "MERGE (o:Entity {name: $o}) "
            f"MERGE (s)-[r:{edge}]->(o) "
            "SET r.source_article_id = $aid"
        )
        self._driver.execute_query(query, s=subject, o=obj, aid=source_article_id)

    def relations_of(
        self, name: str, *, hops: int = 1, limit: int = 25
    ) -> list[tuple[str, str, str, int]]:
        """종목/엔티티에서 나가는 관계 회수(최대 hops홉 — 다홉 추론). 근거 기사 id 동반."""
        if not 1 <= hops <= 3:  # 화이트리스트: 정수 검증 후에만 Cypher에 인라인(주입 차단)
            raise ValueError(f"hops는 1..3이어야 함: {hops}")
        query = (
            f"MATCH p = (s:Entity {{name: $n}})-[r*1..{hops}]->(o:Entity) "
            "UNWIND relationships(p) AS rel "
            "RETURN DISTINCT startNode(rel).name AS subject, type(rel) AS edge, "
            "endNode(rel).name AS object, rel.source_article_id AS aid LIMIT $lim"
        )
        result = self._driver.execute_query(query, n=name, lim=limit)
        return [
            (rec["subject"], rec["edge"], rec["object"], rec["aid"])
            for rec in result.records
        ]
