# 20260725-task-scenario-template.md

> 라운드 ㊳ (시나리오 템플릿 관리 — 운영자 편집). admin 도메인 확장, ADR 0016 연계.
> 계약: `api-contract-scenario-template.py`. admin 서비스(admin_db) + content(전달) + agent(사용).

## 1. Requirements
- **문제(§6)**: 대본 형식(breaking/analysis/story)이 agent `_TEMPLATES`에 **하드코딩** → 운영자가 스타일을 못 추가·편집.
- **관점**: 대본 = **Evidence(시세·기사·거시·관계) + 형식(템플릿)**. Evidence는 데이터, **형식은 운영자가 관리**하면 일관성+다양성.
- **목표**: 현 템플릿 노브(`facts·relations·macro·closing·hook`)를 **admin_db로 승격**, 대시보드에서 CRUD, 대본 생성 시 사용.
- **가드레일(알파①)**: 템플릿은 **구조·톤만** 제어. 수치는 price/macro, 관계는 그래프 근거 — 템플릿이 사실을 만들지 않음(자유 프롬프트 금지).
- **Acceptance Criteria**:
  - [ ] AC1: `admin_db.scenario_template` + CRUD API. 기본 3종 시드(속보/분석/스토리). **검증: 시드 3행, API list/create/update/delete.**
  - [ ] AC2: 대시보드 설정에서 템플릿 추가·편집·토글 → admin_db 반영. **검증: UI→API→DB 왕복.**
  - [ ] AC3: 대본 생성 시 **선택 템플릿의 노브가 반영**(facts 수·관계 수·macro·closing·hook 톤). **검증: 다른 템플릿 → 다른 구조의 대본.**
  - [ ] AC4: 하위호환 — agent `build_script`가 템플릿 정의를 인자로 받되 미지정 시 기본(분석형). 기존 대본 생성 안 깨짐. **검증: 기본 호출 회귀 통과.**
  - [ ] AC5: 가드레일 — 수치·관계는 Evidence에서(템플릿 무관), 무출처 0·로컬 Ollama 불변.

## 2. 핵심 결정 & 사각지대
- **결정 1 — 구조형 템플릿**(자유 프롬프트 아님): 노브(facts/relations/macro/closing/hook)만. 자유 프롬프트는 LLM 환각 위험(알파① 위배)이라 기각.
- **결정 2 — admin 소유**: 템플릿은 운영자 설정 → admin_db(㉝ 연장). 대시보드 쓰기, content/agent가 API로 읽기(Database per Service).
- **결정 3 — 흐름**: 대시보드 선택 → content가 admin에서 정의 조회 → agent에 전달. agent는 무상태(정의를 인자로).
- **사각지대**: agent `build_script` 시그니처 변경(template 문자열 → ScenarioTemplate 정의). 호출부(content consumer) 갱신. 기존 `_TEMPLATES` 제거·시드로 이관. ㉝(admin 서비스) 선행 필요(admin_db 존재 전제) → ㉝ P1 이후.

## 3. UI/UX
- 대시보드 **설정 > 시나리오 템플릿**: 목록·추가·편집(노브 폼)·토글·삭제. 마법사의 템플릿 선택이 이 목록에서 옴.

## 4. Logic
- **admin**: `scenario_template` 테이블 + CRUD API(`TemplateApi`). 시드 3종.
- **content**: 대본 생성 시 선택 template_id로 admin `GET /admin/templates/{id}` 조회 → agent `/agent/script`에 정의 전달.
- **agent `build_script`**: 하드코딩 `_TEMPLATES.get(name)` → **전달받은 `ScenarioTemplate`** 사용(n_facts·n_relations·use_macro·use_closing·hook_tone). 미지정 시 기본.

## 5. File Map
- `[Mod] services/admin/…` — `scenario_template` 모델·CRUD·시드 (㉝ admin 위에)
- `[Mod] services/content/…` — 템플릿 조회·전달
- `[Mod] services/agent/app/script/builder.py` — `build_script`가 템플릿 정의 인자, `_TEMPLATES` 제거
- `[Mod] services/content/app/static/index.html`·`ui_router.py` — 설정 템플릿 CRUD 화면
- `[New] doc/design/admin/api-contract-scenario-template.py`

## 6. Verification
- 단위: build_script가 정의별 다른 구조(AC3)·기본 fallback(AC4). admin CRUD.
- 통합: 대시보드에서 새 템플릿 생성 → 그 템플릿으로 대본 생성 → 구조 반영 확인.
- 가드레일: 수치·관계 Evidence 유래 불변. mypy·계약·회귀.

## 7. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /design | 시나리오 템플릿 관리(운영자). 현 하드코딩 노브(facts/relations/macro/closing/hook)를 admin_db로 승격, 대시보드 CRUD, agent가 정의 인자로 사용. 구조형(자유 프롬프트 기각·알파① 보존). ㉝ admin 연장(admin_db 선행). 계약 mypy 통과. 기본 3종 시드로 하위호환. |
