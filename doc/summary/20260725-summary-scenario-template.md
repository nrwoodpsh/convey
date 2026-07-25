# 20260725 — 요약: 시나리오 템플릿 관리 (라운드㊳)

- **Task**: `doc/design/admin/20260725-task-scenario-template.md` · 계약 `api-contract-scenario-template.py` · ADR 0016(admin 확장)
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: AC1·AC3·AC4·AC5 완료·검증. AC2(템플릿 편집 UI)는 부분(선택 배선만, CRUD 편집 화면은 M2 이관).

## 개요

대본 형식(속보/분석/스토리)이 agent `_TEMPLATES`에 **하드코딩**돼 운영자가 못 바꿨다(㊳). 이 노브(사실 수·관계 수·거시·마무리·훅 톤)를 **admin_db로 승격**해 CRUD하고, 대본 생성 시 content가 admin에서 조회해 agent에 전달한다. 수치·관계는 Evidence(price/macro/그래프)에서 오고 템플릿은 **구조·톤만** 제어(알파① — 템플릿이 사실을 만들지 않음).

## 변경사항 (BE)

- **admin**: `scenario_template` 모델(id·name·n_facts·n_relations·use_macro·use_closing·hook_tone·enabled) + repository·service·router CRUD(`GET/POST/PUT/DELETE /admin/templates`) + 시드 3종(`seed_templates`, 멱등) + 마이그레이션 `0002_scenario_template`.
- **agent**: `_TEMPLATES` dict **제거** → `ScenarioKnobs` dataclass + `_DEFAULT_KNOBS`(분석형). `build_script(..., knobs=None, ...)`(미지정 시 기본). `main.ScriptReq`에 `template_def`(노브) 수용 → `ScenarioKnobs`로 변환해 전달.
- **content**: `admin_client.fetch_template_def(id)`(신규, GET /admin/templates/{id}, HMAC, 실패 시 None). `consumer.handle_generate`가 `template_id`로 노브 조회 → agent에 `template_def` 전달. `service.start_generation`/schemas/ui_router `template`(문자열) → `template_id`(int). `config.admin_url` 추가.
- **content UI**: `index.html` 템플릿 칩 `data-v`를 admin_db template_id(1속보·2분석·3스토리)로, JS `wz.template_id` 전송.

## API 변경

- **admin 신규**: `GET /admin/templates`·`GET /admin/templates/{id}`·`POST`·`PUT /admin/templates/{id}`·`DELETE /admin/templates/{id}`(east-west HMAC).
- **content→agent `/agent/script`**: 요청 필드 `template`(문자열) → `template_def`(노브 객체 또는 null).
- **대시보드 `/ui/generate`**: `template`(문자열) → `template_id`(int|null).

## 검증

- 단위: agent 5(노브 구조차이 AC3·기본형 AC4·기존 회귀 3), admin 2(시드 3종·기본형 노브 일치). mypy `--strict` 0(admin 6·agent 2·content 6), 계약 mypy 0.
- **실스택**(재빌드 admin·agent·content):
  - 마이그레이션 0002 → `scenario_template` 생성, 시드 **3종**(속보 사실1·거시X / 분석 사실3·거시O / 스토리 사실2·마무리O).
  - CRUD 왕복: `POST` id=4·`DELETE` 200·삭제후 `GET` 404.
  - content `fetch_template_def`: id1(사실1·마무리X) vs id3(사실2·마무리O) 노브 차이 라이브 확인.

## 특이사항 (설계 대비·후속)

- **이탈 (a) seed 이벤트루프**: `asyncio.run(seed()); asyncio.run(seed_templates())`가 asyncpg 엔진 풀을 두 루프에 물려 `attached to a different loop` 오류 → `seed_all()`로 단일 루프에서 순차 실행.
- **이탈 (b) SERIAL 시퀀스**: 명시적 id(1·2·3) 시드는 시퀀스를 전진시키지 않아 신규 `POST`가 id=1과 PK 충돌(500) → 시드 끝에 `setval(pg_get_serial_sequence(...), MAX(id))`로 보정(멱등).
- **범위 (AC2)**: 마법사의 **템플릿 선택**은 admin_db template_id로 배선 완료. **템플릿 편집 화면**(대시보드에서 추가·수정·토글)은 M2 대시보드 리디자인으로 이관(㉝ P2 설정 UI와 함께). 현재 편집은 admin API 직접 호출로 가능.
- **알파①**: 템플릿은 구조·톤만. 수치 슬롯·citation guard·무출처 0·로컬 Ollama 불변.
- 커밋: 아직(사람 게이트 — `/commit`).
