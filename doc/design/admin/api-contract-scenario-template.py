"""타입 계약 — 시나리오 템플릿 관리(운영자). 라운드㊳. ADR 0016(admin) 확장.

검증: python -m mypy --strict --ignore-missing-imports api-contract-scenario-template.py

배경(§6): 대본 형식(breaking/analysis/story)이 agent `_TEMPLATES`에 하드코딩 → 운영자가 못 바꿈.
현 템플릿 = {facts:몇, relations:몇, macro:on/off, closing:on/off, hook:톤} — 정확히 운영자 노브.
이를 admin_db로 승격해 대시보드에서 CRUD, 대본 생성 시 재료(Evidence)와 함께 사용.

가드레일(알파①): 템플릿은 **구조·톤만** 제어. 수치는 price/macro, 관계는 그래프 근거에서 —
템플릿이 사실을 만들지 않음(자유 프롬프트 금지·환각 유발 X).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ScenarioTemplate:
    """운영자 편집 시나리오 템플릿 — agent 기존 노브를 DB로 승격."""

    id: int
    name: str            # "급등락 속보형" 등
    description: str
    n_facts: int         # 사용할 사실 개수
    n_relations: int     # 사용할 그래프 관계 개수
    use_macro: bool      # 거시 문장 포함
    use_closing: bool    # 마무리 문장 포함
    hook_tone: str       # 훅 톤 문구(예: "속보 톤(급박하게)")
    enabled: bool = True


# 기본 시드(하위호환) — 기존 3종을 admin_db에 시드.
SEED_TEMPLATES: tuple[ScenarioTemplate, ...] = (
    ScenarioTemplate(1, "속보형", "급등락 속보", 1, 1, False, False, "속보 톤(급박하게)"),
    ScenarioTemplate(2, "분석형", "담백한 분석", 3, 2, True, False, "담백한 분석 톤"),
    ScenarioTemplate(3, "스토리형", "이야기 도입", 2, 1, True, True, "이야기를 여는 도입 톤"),
)


# ── admin 서비스 API (대시보드 CRUD) ──
class TemplateApi(Protocol):
    def list_templates(self) -> list[ScenarioTemplate]: ...              # GET /admin/templates
    def get_template(self, tid: int) -> ScenarioTemplate: ...            # GET /admin/templates/{id}
    def create_template(self, t: ScenarioTemplate) -> ScenarioTemplate: ...   # POST /admin/templates
    def update_template(self, tid: int, t: ScenarioTemplate) -> ScenarioTemplate: ...  # PUT ...
    def delete_template(self, tid: int) -> None: ...                     # DELETE /admin/templates/{id}


# ── 대본 생성 흐름(변경) ──
# 대시보드에서 템플릿 선택 → content가 admin API로 템플릿 정의 조회 → agent /agent/script에 전달.
# agent build_script: 하드코딩 `_TEMPLATES.get(name)` → 전달받은 ScenarioTemplate 사용
#   (n_facts·n_relations·use_macro·use_closing·hook_tone). 미지정 시 기본(분석형) fallback.
NOTE = (
    "agent build_script가 템플릿 정의를 인자로 받음(하드코딩 제거). 수치·관계는 Evidence에서(알파① 불변). "
    "admin_db.scenario_template + 대시보드 CRUD. Database per Service — agent/content는 admin API로 읽음."
)
