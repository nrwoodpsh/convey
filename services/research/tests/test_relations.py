"""라운드① 관계추출 검증 — 환각 방지 필터가 핵심(알파1). LLM은 스텁으로 결정론 검증."""
from __future__ import annotations

from app.extract.relations import extract_relations


def test_drops_out_of_scope_entity() -> None:
    def stub(_: str) -> str:
        return (
            '[{"subject":"삼성전자","edge":"COMPETES","object":"SK하이닉스"},'
            '{"subject":"애플","edge":"COMPETES","object":"삼성전자"}]'
        )

    rels = extract_relations("...", ["삼성전자", "SK하이닉스"], stub)
    assert len(rels) == 1  # 애플(허용 밖)이 든 관계는 폐기
    assert rels[0].subject == "삼성전자" and rels[0].object == "SK하이닉스"


def test_drops_unknown_edge() -> None:
    def stub(_: str) -> str:
        return '[{"subject":"삼성전자","edge":"FAKE_EDGE","object":"SK하이닉스"}]'

    assert extract_relations("...", ["삼성전자", "SK하이닉스"], stub) == []


def test_tolerates_wrapping_text() -> None:
    def stub(_: str) -> str:
        return '설명\n[{"subject":"삼성전자","edge":"BELONGS_TO","object":"반도체"}]\n끝'

    rels = extract_relations("...", ["삼성전자", "반도체"], stub)
    assert len(rels) == 1 and rels[0].edge == "BELONGS_TO"


def test_empty_on_garbage() -> None:
    assert extract_relations("...", ["삼성전자"], lambda _: "관계 없음") == []
