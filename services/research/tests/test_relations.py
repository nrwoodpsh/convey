"""라운드① 관계추출 검증 — 환각 방지 필터가 핵심(알파1). LLM은 스텁으로 결정론 검증."""
from __future__ import annotations

from app.extract.relations import extract_article_graph, extract_graph, extract_relations


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


# ── 요약 선행 NER(㉛) — 원문 검증으로 요약 환각 차단 ──
def test_verify_text_drops_summary_hallucination() -> None:
    """요약 위에서 NER하되 검증은 원문(verify_text) — 요약이 지어낸 엔티티는 폐기(알파1)."""
    body = "삼성전자가 HBM을 공급한다."  # 원문
    summary = "삼성전자가 젠슨황과 협력한다."  # 요약 — '젠슨황'은 원문에 없음(요약 환각)

    def stub(_: str) -> str:
        return '{"entities":["삼성전자","젠슨황"],"relations":[]}'

    g = extract_graph(summary, ["삼성전자"], stub, verify_text=body)
    assert "삼성전자" in g.entities  # seed
    assert "젠슨황" not in g.entities  # 원문에 없음 → 폐기(요약 환각컷)


def test_article_graph_long_uses_summary() -> None:
    """긴 본문(>임계)은 요약 caller를 1회 호출하고 요약 위에서 NER."""
    body = "가" * 1600  # > SUMMARY_THRESHOLD(1500)
    calls = {"summary": 0}

    def summary_llm(_: str) -> str:
        calls["summary"] += 1
        return "삼성전자 관련 요약"

    def ner_llm(_: str) -> str:
        return '{"entities":["삼성전자"],"relations":[]}'

    g = extract_article_graph(body, ["삼성전자"], ner_llm, summary_llm)
    assert calls["summary"] == 1  # 요약 호출됨
    assert "삼성전자" in g.entities


def test_article_graph_short_skips_summary() -> None:
    """짧은 본문(≤임계)은 요약을 건너뛰고 원문 그대로 NER."""
    body = "삼성전자가 상승했다."  # < 1500
    calls = {"summary": 0}

    def summary_llm(_: str) -> str:
        calls["summary"] += 1
        return "x"

    def ner_llm(_: str) -> str:
        return '{"entities":["삼성전자"],"relations":[]}'

    g = extract_article_graph(body, ["삼성전자"], ner_llm, summary_llm)
    assert calls["summary"] == 0  # 요약 미호출
    assert "삼성전자" in g.entities


# ── 온톨로지 확장(㉟) — 타입 검증 · 엣지 domain/range · event 속성 ──
def test_edge_domain_range_drops_misuse() -> None:  # AC2
    text = "삼성전자가 반도체 분야에서 실적을 냈다."

    def stub(_: str) -> str:
        return (
            '{"entities":[{"name":"삼성전자","type":"기업"},{"name":"반도체","type":"섹터"}],'
            '"relations":[{"subject":"삼성전자","edge":"HAS_EVENT","object":"반도체"},'
            '{"subject":"삼성전자","edge":"BELONGS_TO","object":"반도체"}]}'
        )

    g = extract_graph(text, [], stub)
    edges = {(r.subject, r.edge, r.object) for r in g.relations}
    assert ("삼성전자", "BELONGS_TO", "반도체") in edges   # 기업→섹터 OK
    assert ("삼성전자", "HAS_EVENT", "반도체") not in edges  # 목적어=섹터 → 폐기(사건이어야)


def test_new_edge_partners_accepted() -> None:  # AC1 — 확장 엣지
    text = "삼성전자와 엔비디아가 협력한다."

    def stub(_: str) -> str:
        return (
            '{"entities":[{"name":"삼성전자","type":"기업"},{"name":"엔비디아","type":"기업"}],'
            '"relations":[{"subject":"삼성전자","edge":"PARTNERS_WITH","object":"엔비디아"}]}'
        )

    g = extract_graph(text, [], stub)
    assert any(r.edge == "PARTNERS_WITH" for r in g.relations)


def test_event_type_direction_parsed() -> None:  # AC3
    text = "삼성전자가 유상증자를 결정했다."

    def stub(_: str) -> str:
        return (
            '{"entities":[{"name":"삼성전자","type":"기업"},'
            '{"name":"유상증자","type":"사건","event_type":"유상증자","direction":"부정"}],'
            '"relations":[]}'
        )

    g = extract_graph(text, [], stub)
    assert "유상증자" in g.entities
    assert g.events.get("유상증자") == ("유상증자", "부정")


def test_type_validation_drops_disallowed() -> None:  # 타입 허용 밖 폐기
    text = "삼성전자 노조가 파업했다."

    def stub(_: str) -> str:
        return (
            '{"entities":[{"name":"삼성전자","type":"기업"},{"name":"노조","type":"조직"}],'
            '"relations":[]}'
        )

    g = extract_graph(text, [], stub)
    assert "삼성전자" in g.entities
    assert "노조" not in g.entities  # 타입 '조직'(허용 밖) + 스톱워드 → 폐기
