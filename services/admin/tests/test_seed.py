"""시드 로직 검증(㉝ P1) — common.stocks 승격이 결정론적으로 행을 만든다."""
from __future__ import annotations

from app.seed import _SEED_TEMPLATES, _static_rows


def test_static_rows_from_stocks() -> None:
    rows = _static_rows()
    assert len(rows) >= 40  # common.stocks(현 46)
    by_ticker = {r["ticker"]: r for r in rows}
    assert "005930" in by_ticker
    assert by_ticker["005930"]["name"] == "삼성전자"
    # 모든 행에 ticker·name 존재(무출처 없음)
    assert all(r["ticker"] and r["name"] for r in rows)


def test_seed_templates_default_three() -> None:
    """㊳ — 기본 3종(속보·분석·스토리) id 고정, 분석형 노브가 하위호환 기본과 일치."""
    by_id = {t["id"]: t for t in _SEED_TEMPLATES}
    assert set(by_id) == {1, 2, 3}
    assert by_id[2]["name"] == "분석형"
    assert by_id[2]["n_facts"] == 3 and by_id[2]["use_macro"] is True
    assert by_id[1]["use_macro"] is False  # 속보형: 거시 없음
    assert by_id[3]["use_closing"] is True  # 스토리형: 마무리 있음
