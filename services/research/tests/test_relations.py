"""라운드① 관계추출 검증 — 환각 방지 필터가 핵심(알파1). LLM은 스텁으로 결정론 검증."""
from __future__ import annotations

from app.extract.relations import extract_graph, extract_relations


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


# ── 개방형 NER(㉚) ──
def test_extract_graph_substring_and_edge_filter() -> None:
    text = "삼성전자가 젠슨황과 만났다. HBM 협력 논의."

    def stub(_: str) -> str:
        # 젠슨황은 본문 실재(채택), 존재하지않는기업은 환각(폐기). 엣지 FAKE는 폐기.
        return (
            '{"entities":["삼성전자","젠슨황","존재하지않는기업","시장"],'
            '"relations":[{"subject":"삼성전자","edge":"AFFECTS","object":"젠슨황"},'
            '{"subject":"삼성전자","edge":"FAKE","object":"젠슨황"}]}'
        )

    g = extract_graph(text, ["삼성전자"], stub)
    assert "젠슨황" in g.entities  # 본문 실재 → 채택
    assert "존재하지않는기업" not in g.entities  # 환각(본문에 없음) → 폐기
    assert "시장" not in g.entities  # 스톱워드 → 폐기
    assert "삼성전자" in g.entities  # seed 합집
    assert len(g.relations) == 1 and g.relations[0].edge == "AFFECTS"  # FAKE 엣지 폐기
