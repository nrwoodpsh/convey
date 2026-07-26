# 20260726 — 요약: YouTube 발행 + Supabase 인증 활성화 (라운드㊶ M4)

- **Task**: `doc/design/publishing/20260725-task-publish-youtube.md` · 계약 `api-contract-publish-youtube.py` · ADR 0007·0010
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 단위 + 실스택
- **상태**: AC1~AC6 완료·검증. 2차 상품화의 마지막 관문(발행·인증) 코드 완비 — 실 외부 키만 사람 게이트.

## 개요

완성본(mp4)까지 전자동이던 파이프라인에 **YouTube 자동 발행(C1)**과 **Supabase 인증 활성화(C2)**를 붙였다(㊶). 발행은 **사람이 대시보드 "발행" 버튼을 눌러야만**(`content.approved`) 트리거되고 기본 비공개(private)로 업로드한다. 인증 코드(게이트웨이 JWKS)는 이미 활성 — 실 Supabase 프로젝트 키 주입만 남는다.

## 변경사항 (BE)

- **publishing `youtube.py`**: 스텁 → 실 OAuth2 refresh-token 업로드(google-api-python-client, resumable). `build_description`(제목+면책+출처 계승). 자격증명 3종 없으면 `configured=False`·`NotImplementedError`(skip). 기본 `privacy=private`.
- **publishing `consumer.py`**: 강화 이벤트(mp4_path·title·sources) 소비 → `build_description` → 업로드. **멱등**(이미 published면 재업로드 skip) + 실패 기록(재시도 가능). 발행은 `content.approved`만 트리거.
- **publishing `config.py`**: `youtube_client_id/secret/refresh_token`·`youtube_privacy`·`media_dir`. **pyproject**: google-api-python-client·google-auth.
- **content `service.approve`**: `content.approved` 이벤트 강화 — mp4_path(Content)·title(topic)·sources(Script citations 호스트). publishing이 출처·면책 description을 그대로 구성.
- **content `ui_router`**: `POST /ui/jobs/{id}/publish`(발행 승인, ready만) · `GET /ui/publishing/{id}`(상태 중계). `dashboard.fetch_publish_status`. config `publishing_url`.
- **content FE**: 완성본 미리보기에 발행 버튼(사람 클릭) + 상태(대기/업로드/실패/발행됨 YouTube 링크).
- **ADR 0010**: 대시보드 노출 M4 확정(개발=로컬 전용, 배포=게이트웨이 뒤).

## API 변경

- **content 신규(무인증 /ui)**: `POST /ui/jobs/{id}/publish`·`GET /ui/publishing/{id}`.
- **content.approved 이벤트 강화**: `{job_id, content_id}` → `+ mp4_path, title, sources`.
- publishing `GET /publishing/{id}`(기존) 소비. gateway JWKS 검증(기존, 활성).

## 검증

- 단위: publishing 4(build_description 면책·출처 dedup / configured 키게이팅 / upload skip) + 인증 7(`test_supabase_auth` 유효·wrong-aud·만료·issuer·위조). mypy `--strict` 0(publishing 3·content 4), 계약 0. JS `node --check` OK.
- **실스택**(재빌드 publishing·content, google 라이브러리 설치):
  - youtube 미연결: 키 없음 → `configured=False`, description 면책·출처 포함.
  - 멱등: 재enqueue 동일 레코드 / published 후 enqueue → skip 조건 True / external_url 보존.
  - 가드레일: 비-ready 잡 발행 POST → 409. `/ui/publishing/999999` → status none.
  - **e2e**: ready 잡(job45) 발행 승인 → job approved → `content.approved`(강화) 발행 → publishing 소비 → 무자격증명이라 `failed`("YouTube OAuth 자격증명 없음 — 발행 승인·.env 주입 후 연결"). 발행 체인 전체 작동(실 업로드만 OAuth 게이트).

## 특이사항 (설계 대비·후속)

- **사람 게이트**: 실 YouTube 업로드(OAuth client_id/secret/refresh_token)·실 Supabase 프로젝트 키는 `.env` 주입 후에만. 코드·폴백·멱등·description·JWKS 검증까지 검증 완료.
- **e2e 잔여 상태**: 검증에서 job45(content 35)가 approved + publish failed로 전이(무자격증명). 키 주입 후 재발행 가능(멱등 — 실패는 재시도 허용). 되돌리지 않음(실제 파이프라인 동작 반영).
- **가드레일**: 자동 발행 금지(사람 클릭만)·기본 private·출처/면책 description·키 커밋 0(.env.example엔 이름만). 원문 텍스트 외부 미전달(mp4+메타만).
- **후속**: 대용량 mp4 업로드 재개(resumable next_chunk 진행률)·할당량·공개 전환(수동)은 키 발급 후 튜닝.
- 커밋: 아직(사람 게이트 — `/commit`).
