"""그래프 리포 결정론 검증 — 허용 밖 엣지는 드라이버에 닿기 전 거부(주입·오타 차단)."""
from __future__ import annotations

import pytest

from app.graph.neo4j_repo import GraphRepo


def test_upsert_rejects_non_whitelisted_edge() -> None:
    repo = GraphRepo(driver=None)  # 검증이 먼저라 driver는 쓰이지 않음
    with pytest.raises(ValueError):
        repo.upsert_relation("삼성전자", "FAKE_EDGE", "SK하이닉스", source_article_id=1)
