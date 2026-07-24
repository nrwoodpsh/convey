"""num_predict(출력 상한) 페이로드 구성 검증 — 요약 호출 타임아웃 방지(㉛)."""
from __future__ import annotations

from app.ollama_client import build_generate_payload


def test_payload_omits_options_when_no_limit() -> None:
    """num_predict 미지정 → options 미포함(기존 호출과 완전 동일·하위호환)."""
    p = build_generate_payload("llama3.2", "안녕", None)
    assert p == {"model": "llama3.2", "prompt": "안녕", "stream": False}
    assert "options" not in p


def test_payload_includes_num_predict_when_set() -> None:
    """num_predict 지정 → options.num_predict 포함(Ollama 출력 상한)."""
    p = build_generate_payload("llama3.2", "요약해", 256)
    assert p["options"] == {"num_predict": 256}
    assert p["prompt"] == "요약해"


def test_payload_think_and_keep_alive() -> None:
    """think=False·keep_alive 지정 → payload 포함(추론 억제·모델 상주, ㉛)."""
    p = build_generate_payload("qwen3:14b", "요약해", 256, think=False, keep_alive="30m")
    assert p["think"] is False
    assert p["keep_alive"] == "30m"


def test_payload_omits_think_keepalive_when_none() -> None:
    """미지정 시 think·keep_alive 키 없음(하위호환)."""
    p = build_generate_payload("llama3.2", "안녕", None)
    assert "think" not in p and "keep_alive" not in p
