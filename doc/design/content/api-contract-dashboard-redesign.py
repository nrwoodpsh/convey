"""타입 계약 — 운영 대시보드 리디자인(M2). 라운드㊵. ADR 0010 확장.

검증: python -m mypy --strict --ignore-missing-imports api-contract-dashboard-redesign.py

배경: 현 대시보드(:8091, 탭·마법사)는 생성 흐름 위주. M1에서 만든 설정(admin ㉝·템플릿 ㊳·배경 ㊴)과
근거(관계·출처)·품질 지표를 담도록 재설계. content 서비스가 admin API를 east-west로 읽어 화면 구성.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

# 대시보드 상단 영역(정보구조 개편)
NavSection = Literal["today", "shorts", "settings"]  # 오늘자 기사 · 생성 쇼츠 · 설정(신규)
SettingsTab = Literal["stocks", "keywords", "sources", "period", "templates", "backgrounds"]


@dataclass
class EvidenceView:
    """시나리오/완성본에 붙는 근거 노출 — 관계(그래프)·출처 URL. 신뢰 강화(알파①)."""

    relations: list[str] = field(default_factory=list)   # "삼성전자 —[경쟁]→ SK하이닉스"
    sources: list[str] = field(default_factory=list)     # 출처 URL 목록
    prices: list[str] = field(default_factory=list)      # 수치(종가·등락)


@dataclass
class QualityMetrics:
    """대시보드 품질 뷰 — 운영자가 파이프라인 상태를 한눈에."""

    graph_nodes: int = 0
    graph_relations: int = 0
    articles_today: int = 0
    issues_selected: int = 0
    jobs_ready: int = 0


@dataclass
class DashboardHome:
    """리디자인 홈 뷰모델 — 탭(오늘자/쇼츠/설정) + 품질 지표."""

    section: NavSection
    metrics: QualityMetrics


# ── content 대시보드 라우트(신규/변경) — 설정은 admin API 프록시 ──
class DashboardApi(Protocol):
    def home(self) -> DashboardHome: ...                        # GET /ui  (지표 포함)
    def evidence(self, job_id: int) -> EvidenceView: ...        # GET /ui/jobs/{id}/evidence (근거)
    # 설정 화면 — content가 admin API를 east-west로 중계(Database per Service)
    def settings(self, tab: SettingsTab) -> dict[str, object]: ...   # GET /ui/settings/{tab}
    def settings_save(self, tab: SettingsTab, body: dict[str, object]) -> None: ...  # PUT/POST


NOTE = (
    "탭: 오늘자 기사·생성 쇼츠·**설정(신규)**. 설정은 admin(㉝·㊳·㊴) 데이터를 content가 중계. "
    "근거(관계·출처) 뷰·품질 지표 추가. 기존 마법사(시나리오 승인·배경 선택) 흐름은 유지·정돈. "
    "무인증 로컬 전용(ADR 0010) — M4에서 게이트웨이 뒤로."
)
