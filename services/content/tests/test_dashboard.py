"""대시보드 근거 조립 검증(㊵ P1) — Script → 관계·출처·수치(순수 함수)."""
from __future__ import annotations

from app.dashboard import build_evidence


def test_build_evidence_splits_kinds() -> None:
    sections = [
        {"kind": "hook", "text": "도입"},
        {"kind": "chart", "text": "현대차 종가 {close}원, 등락률 {change_pct}%",
         "data_slots": {"close": "200,000", "change_pct": "+1.5"}},
        {"kind": "relation", "text": "현대차 —[공급]→ 현대모비스"},
        {"kind": "fact", "text": "실적 호조"},
    ]
    citations = [
        {"claim": "a", "source_url": "https://n/1", "ref_id": 1},
        {"claim": "b", "source_url": "https://n/1", "ref_id": 2},  # 중복 URL
        {"claim": "c", "source_url": "https://n/2", "ref_id": 3},
    ]
    ev = build_evidence(sections, citations)
    assert ev["relations"] == ["현대차 —[공급]→ 현대모비스"]
    assert ev["prices"] == ["현대차 종가 200,000원, 등락률 +1.5%"]  # 슬롯 치환(사실값)
    assert ev["sources"] == ["https://n/1", "https://n/2"]  # 중복 제거·순서 보존


def test_build_evidence_empty() -> None:
    ev = build_evidence([], [])
    assert ev == {"relations": [], "sources": [], "prices": []}
