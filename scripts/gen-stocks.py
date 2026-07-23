"""종목 마스터 생성(㉙/E1) — pykrx로 KOSPI 시총 상위 N의 ticker→한글명을 뽑아
libs/common/common/stocks.py의 STOCK_NAMES 블록을 재생성한다(정적 커밋, 런타임 의존 X).

사람이 실행(네트워크·pykrx 필요):
  docker compose exec market-feed python - < scripts/gen-stocks.py        # 컨테이너(pykrx 有)
  # 또는 로컬(pykrx 설치 시): python scripts/gen-stocks.py
STOCK_NAMES 마커(# <gen:names> ... # </gen:names>) 사이만 치환. STOCK_SECTOR·함수는 보존.
섹터 자동 분류는 pykrx 미지원 → STOCK_SECTOR는 수기 유지(후속: KRX 업종 매핑).
"""
from __future__ import annotations

import re
import sys

TOP_N = 40  # 시총 상위 N (name 조회 호출 수 고려)
STOCKS_PY = "libs/common/common/stocks.py"


def generate() -> dict[str, str]:
    from pykrx import stock

    day = stock.get_nearest_business_day_in_a_week()
    cap = stock.get_market_cap_by_ticker(day, market="KOSPI")  # 시총 DataFrame
    top = cap.sort_values("시가총액", ascending=False).head(TOP_N).index.tolist()
    names: dict[str, str] = {}
    for t in top:
        try:
            names[str(t)] = stock.get_market_ticker_name(str(t))
        except Exception:  # noqa: BLE001 — 개별 실패는 건너뜀
            continue
    return names


def render_block(names: dict[str, str]) -> str:
    lines = [f'    "{t}": "{n}",' for t, n in names.items()]
    return "# <gen:names>\nSTOCK_NAMES: dict[str, str] = {\n" + "\n".join(lines) + "\n}\n# </gen:names>"


def main() -> None:
    names = generate()
    block = render_block(names)
    # 파일이 있으면 마커 사이 치환, 없으면 블록만 출력(사람이 병합)
    try:
        with open(STOCKS_PY, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        print(block)
        return
    if "# <gen:names>" in src:
        new = re.sub(r"# <gen:names>.*?# </gen:names>", block, src, flags=re.S)
        with open(STOCKS_PY, "w", encoding="utf-8") as f:
            f.write(new)
        sys.stderr.write(f"STOCK_NAMES {len(names)}종목 재생성 → {STOCKS_PY}\n")
    else:
        print(block)


if __name__ == "__main__":
    main()
