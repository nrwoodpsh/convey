# 20260725-task-publish-youtube.md

> 라운드 ㊶ (M4 — YouTube 자동 발행 C1 + Supabase 인증 활성화 C2). ADR 0007·0010.
> 계약: `api-contract-publish-youtube.py`. publishing 서비스 + gateway/대시보드. 외부 키 필요.

## 1. Requirements
- **문제**: 완성본(mp4)까지 전자동이나 **발행 미구현**(`publishing/youtube.py` 스텁). 인증도 게이트웨이 JWKS **코드만** 있고 미활성(C2). = 2차 상품화의 마지막 관문.
- **목표**: ①**YouTube 자동 발행** — 사람 승인(`content.approved`) 후 mp4 업로드. ②**Supabase 인증 활성화** + 대시보드 노출 정리.
- **가드레일**: **자동 발행 금지 — 사람 승인 후에만.** 기본 비공개(private). 출처·면책 계승. 키는 `.env`(커밋 금지).
- **Acceptance Criteria**:
  - [ ] AC1: `content.approved`(승인) 소비 → mp4 **YouTube 업로드**, `youtube_id` 기록. **검증: 승인 이벤트 1건 → 업로드(테스트: private).**
  - [ ] AC2: **승인 없인 발행 안 함**(가드레일). **검증: 승인 이벤트 없이 완성본 → 업로드 0.**
  - [ ] AC3: 업로드 **멱등·재시도** — 같은 job 재승인 중복 업로드 방지. **검증: 재수신 시 중복 0.**
  - [ ] AC4: **Supabase 활성화** — 실프로젝트 키로 게이트웨이 JWKS 검증 동작(유효 토큰 통과·무효 401). **검증: 유효/무효 토큰.**
  - [ ] AC5: **대시보드 노출 정리** — :8091을 게이트웨이 뒤로(인증) 또는 로컬 전용 유지 확정·적용. **검증: 결정대로 접근 통제.**
  - [ ] AC6: 가드레일 — 기본 private, 출처·면책 description, 키 커밋 0.

## 2. 핵심 결정 & 사각지대
- **결정 1 — 발행은 승인 게이트 뒤**: `content.approved` 소비만 트리거(자동 금지, CLAUDE.md §4).
- **결정 2 — 기본 private**: 안전. 운영자가 나중에 공개 전환(수동).
- **결정 3 — 대시보드 노출**: (a) 게이트웨이 뒤로(인증 필요) vs (b) 로컬 전용 유지 — 운영 배포 형태에 따라. 기본 권장 = 배포 시 (a).
- **사각지대**: **YouTube OAuth**(구글 클라우드 프로젝트·동의화면·토큰 갱신) — 발급·승인은 사람. 할당량(일 업로드 제한). Supabase 실프로젝트 검증 필요(현 .env 값이 placeholder인지). 업로드 대용량(mp4 수십MB)·재개. 외부 키라 CI/헤드리스에선 스킵.

## 3. UI/UX
- 대시보드에 **발행 버튼**(승인된 완성본에) + 발행 상태(uploading/published/failed)·youtube 링크. 인증 활성 시 로그인 게이트.

## 4. Logic
- **publishing**: `content.approved` 소비 → `YouTubePublisher.upload(mp4, meta)`(google-api-python-client, OAuth 토큰 .env) → `PublishRecord`(publishing_db, 멱등). description에 출처·면책.
- **인증**: Supabase 프로젝트 생성 → `.env` 확인 → 게이트웨이 검증 확인. 대시보드 노출 정리(게이트웨이 라우트 or 유지).

## 5. File Map
- `[Mod] services/publishing/app/youtube.py` — 스텁 → OAuth 업로드 실연결
- `[Mod] services/publishing/app/consumer.py` — `content.approved` 소비·멱등·재시도
- `[Mod] services/content …` — 발행 버튼·상태(대시보드)
- `[Mod] gateway/compose/.env.example` — 대시보드 노출·SUPABASE_*·YOUTUBE OAuth 키 이름
- `[New] doc/design/publishing/api-contract-publish-youtube.py`

## 6. Verification
- 단위/통합: 승인→업로드(private)·미승인→0·멱등. 인증 유효/무효 토큰. 대시보드 접근 통제.
- 가드레일: private 기본·출처 description·키 커밋 0. (실 업로드·키는 사람 게이트.)

## 7. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /design | M4 YouTube 발행(C1)+Supabase 활성화(C2). 발행은 content.approved(사람 승인) 후에만·기본 private·멱등. 게이트웨이 JWKS 코드 완비(ADR 0007) → 활성화만. 대시보드 노출 정리(게이트웨이 뒤 or 로컬). 외부 키(YouTube OAuth·Supabase)는 .env·사람 게이트. 계약 mypy 통과. backlog-deferred C1·C2 해소 설계. |
