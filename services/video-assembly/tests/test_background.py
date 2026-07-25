"""배경 라이브러리 매칭 검증(㊴) — 섹터/태그 매칭 + 파일 존재 + 활성 필터."""
from __future__ import annotations

from pathlib import Path

from app.background import match_background


def _asset(path: str, tags: list[str], enabled: bool = True, kind: str = "image") -> dict:
    return {"id": 1, "name": "t", "tags": tags, "path": path, "kind": kind,
            "license": "CC0", "enabled": enabled}


def test_matches_sector_tag(tmp_path: Path) -> None:
    """자동차 태그 배경 → 현대차(005380, 섹터=자동차) job이 사용(AC1)."""
    f = tmp_path / "car.jpg"
    f.write_bytes(b"x")
    hit = match_background([_asset(str(f), ["자동차"])], "005380")
    assert hit is not None and hit.path == str(f) and hit.license == "CC0"


def test_no_match_other_sector(tmp_path: Path) -> None:
    """반도체 태그는 현대차와 무관 → None(다음 우선순위로 폴백, AC2)."""
    f = tmp_path / "chip.jpg"
    f.write_bytes(b"x")
    assert match_background([_asset(str(f), ["반도체"])], "005380") is None


def test_skips_disabled_and_missing(tmp_path: Path) -> None:
    """비활성·파일없음은 건너뜀(메타만 있고 파일 없으면 폴백)."""
    f = tmp_path / "car.jpg"
    f.write_bytes(b"x")
    assert match_background([_asset(str(f), ["자동차"], enabled=False)], "005380") is None
    assert match_background([_asset(str(tmp_path / "missing.jpg"), ["자동차"])], "005380") is None


def test_matches_by_stock_name(tmp_path: Path) -> None:
    """섹터뿐 아니라 종목명 태그로도 매칭(현대차)."""
    f = tmp_path / "hd.mp4"
    f.write_bytes(b"x")
    hit = match_background([_asset(str(f), ["현대차"], kind="video")], "005380")
    assert hit is not None and hit.kind == "video"
