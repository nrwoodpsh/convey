"""정확한 차트·수치 렌더 — 알파③. 라운드④.

생성형 영상이 못하는 "정확한 숫자를 화면에 박기"를 **결정론적으로** 한다.
수치는 입력(사실 데이터)을 그대로 그린다 — LLM·생성모델이 만들지 않음(환각 0).
matplotlib로 차트+수치 오버레이 PNG를 렌더 → 이후 ffmpeg가 배경 broll·음성과 합성.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib

matplotlib.use("Agg")  # 디스플레이 없는 서버 렌더
import matplotlib.pyplot as plt  # noqa: E402


@dataclass
class ChartOverlay:
    ticker: str
    close: float
    change_pct: float
    series: list[float] = field(default_factory=list)


def format_price(close: float, change_pct: float) -> tuple[str, str]:
    """정확 수치 텍스트 — 입력 그대로 포맷(반올림·부호 규칙만). 값 자체는 불변."""
    return f"{close:,.0f}원", f"{change_pct:+.2f}%"


def render_title_card(title: str, out_path: str) -> str:
    """키 없는 배경 — 외부 broll 대신 로컬 생성 타이틀 카드(9:16 다크). 켄번즈 base로 사용.

    외부 API 없이 배경을 만든다(ADR 0006·0008 — broll/TTS는 키 발급 후). 경로 반환.
    """
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    fig.patch.set_facecolor("#0d1b2a")
    ax.set_facecolor("#0d1b2a")
    ax.text(0.5, 0.5, title, transform=ax.transAxes, ha="center", va="center",
            fontsize=34, color="#e0e1dd", wrap=True)
    ax.axis("off")
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def render_chart(overlay: ChartOverlay, out_path: str) -> str:
    """쇼츠 세로 프레임에 시세 차트 + 정확 수치 오버레이를 렌더해 PNG 저장. 경로 반환."""
    close_text, change_text = format_price(overlay.close, overlay.change_pct)
    color = "#d32f2f" if overlay.change_pct >= 0 else "#1565c0"

    fig, ax = plt.subplots(figsize=(9, 16), dpi=60)  # 9:16 쇼츠
    if overlay.series:
        ax.plot(overlay.series, linewidth=3, color=color)
    ax.text(0.5, 0.92, overlay.ticker, transform=ax.transAxes, ha="center", fontsize=26)
    ax.text(0.5, 0.84, close_text, transform=ax.transAxes, ha="center", fontsize=40, color=color)
    ax.text(0.5, 0.78, change_text, transform=ax.transAxes, ha="center", fontsize=26, color=color)
    ax.axis("off")
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
