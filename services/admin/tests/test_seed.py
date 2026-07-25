"""시드 로직 검증(㉝ P1) — common.stocks 승격이 결정론적으로 행을 만든다."""
from __future__ import annotations

from app.seed import _static_rows


def test_static_rows_from_stocks() -> None:
    rows = _static_rows()
    assert len(rows) >= 40  # common.stocks(현 46)
    by_ticker = {r["ticker"]: r for r in rows}
    assert "005930" in by_ticker
    assert by_ticker["005930"]["name"] == "삼성전자"
    # 모든 행에 ticker·name 존재(무출처 없음)
    assert all(r["ticker"] and r["name"] for r in rows)
