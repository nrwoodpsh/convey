"""샘플 도구 — 새 도구 작성 시 이 형태를 복사."""
from __future__ import annotations


class CalculatorTool:
    name = "calculator"
    description = "간단한 산술식을 계산한다. 입력 예: '2 * (3 + 4)'"

    async def run(self, arg: str) -> str:
        # 데모용. 실제로는 안전한 파서를 쓸 것(eval 금지).
        allowed = set("0123456789+-*/(). ")
        if not set(arg) <= allowed:
            return "지원하지 않는 문자가 포함됨"
        try:
            return str(eval(arg, {"__builtins__": {}}, {}))  # noqa: S307 - 데모 한정
        except Exception as exc:  # noqa: BLE001
            return f"계산 실패: {exc}"
