"""정확한 차트·수치 렌더 — 알파③. 라운드④·㉑.

생성형 영상이 못하는 "정확한 숫자를 화면에 박기"를 **결정론적으로** 한다.
수치는 입력(사실 데이터)을 그대로 그린다 — LLM·생성모델이 만들지 않음(환각 0).
한글은 번들 NanumGothic(OFL)로 렌더(로컬·컨테이너 공통, tofu 방지). 9:16 레이아웃:
상단 제목 · 중앙 큰 라인차트 · 그 아래 대형 종가·등락률. 투명 PNG → ffmpeg가 배경·음성과 합성.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import matplotlib

matplotlib.use("Agg")  # 디스플레이 없는 서버 렌더
from matplotlib import font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# 번들 한글 폰트 등록(로컬·컨테이너 동일). matplotlib·ffmpeg drawtext 공용.
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "NanumGothic.ttf")
if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams["axes.unicode_minus"] = False  # 음수 부호 깨짐 방지


@dataclass
class ChartOverlay:
    ticker: str
    close: float
    change_pct: float
    series: list[float] = field(default_factory=list)
    title: str = ""  # 쇼츠 제목(주제) — 최상단 큰 제목
    stock_label: str = ""  # 종목 라벨 '현대차(005380)' — 코드만 나오지 않게. 비면 ticker 사용


def format_price(close: float, change_pct: float) -> tuple[str, str]:
    """정확 수치 텍스트 — 입력 그대로 포맷(반올림·부호 규칙만). 값 자체는 불변."""
    return f"{close:,.0f}원", f"{change_pct:+.2f}%"


def render_title_card(title: str, out_path: str) -> str:
    """키 없는 배경 폴백 — 로컬 생성 타이틀 카드(9:16 다크). broll 실패 시 배경."""
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    fig.patch.set_facecolor("#0d1b2a")
    ax.set_facecolor("#0d1b2a")
    ax.text(0.5, 0.5, title, transform=ax.transAxes, ha="center", va="center",
            fontsize=44, color="#e0e1dd", wrap=True)
    ax.axis("off")
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def render_chart(overlay: ChartOverlay, out_path: str) -> str:
    """차트+정확 수치를 **투명 1080×1920 PNG**로 렌더(배경 broll 위 오버레이). 레이아웃 존(㉒):
    상단 제목 · 그 아래 종목 라벨 '한글명(코드)' · 중앙 큰 라인차트 · 그 아래 대형 종가·등락률.
    반투명 패널로 가독성. 종목은 코드만 나오지 않게 '현대차(005380)' 형태.
    """
    close_text, change_text = format_price(overlay.close, overlay.change_pct)
    color = "#ff5252" if overlay.change_pct >= 0 else "#448aff"  # 밝은 톤(어두운 배경 대비)
    stock_text = overlay.stock_label or overlay.ticker  # 라벨 비면 코드 폴백

    fig = plt.figure(figsize=(9, 16), dpi=120)  # 1080×1920
    fig.patch.set_alpha(0.0)

    # 최상단: 쇼츠 제목(주제)
    title_box = {"boxstyle": "round,pad=0.5", "facecolor": "black", "alpha": 0.6, "edgecolor": "none"}
    if overlay.title:
        fig.text(0.5, 0.925, overlay.title, ha="center", va="center",
                 fontsize=44, color="white", weight="bold", bbox=title_box, wrap=True)
    # 그 아래: 종목 라벨 '한글명(코드)' (청록 강조)
    fig.text(0.5, 0.86, stock_text, ha="center", va="center",
             fontsize=40, color="#22e0ff", weight="bold", bbox=title_box)

    # 중앙: 큰 라인차트(정확 시계열)
    ax = fig.add_axes((0.10, 0.42, 0.80, 0.34))
    ax.axis("off")
    ax.patch.set_alpha(0.35)  # 차트 영역 살짝 어둡게(선 가독성)
    ax.set_facecolor("black")
    if overlay.series:
        ax.plot(overlay.series, linewidth=6, color=color)
        ax.margins(x=0.02, y=0.15)

    # 그 아래: 대형 종가·등락률
    num_box = {"boxstyle": "round,pad=0.4", "facecolor": "black", "alpha": 0.6, "edgecolor": "none"}
    fig.text(0.5, 0.345, close_text, ha="center", va="center",
             fontsize=76, color=color, weight="bold", bbox=num_box)
    fig.text(0.5, 0.285, change_text, ha="center", va="center",
             fontsize=46, color=color, weight="bold", bbox=num_box)

    fig.savefig(out_path, transparent=True)
    plt.close(fig)
    return out_path
