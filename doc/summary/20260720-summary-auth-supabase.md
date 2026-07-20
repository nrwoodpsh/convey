# 20260720 — 요약: 인증 Supabase 전환 (라운드 0)

- **Task**: `doc/design/auth/task-auth-supabase-20260719.md` (ADR 0007)
- **작업**: /run(design 확정 → builder → sync) · **날짜** 2026-07-20 · **브랜치** main
- **상태**: 구현 완료(단위 검증). 커밋 전 · Supabase 실연동은 사람 게이트.

## 개요

원형의 자체 JWT 발급·검증을 **Supabase Auth 위임**으로 교체했다. 게이트웨이는 Supabase가 발급한 토큰을 **JWKS(비대칭)로 검증**만 하고, 하류 HMAC 신뢰헤더 패턴은 그대로 유지한다.

## 변경사항

**BE**
- `[New] libs/common/common/supabase_auth.py` — `SupabaseVerifier`(JWKS 서명+aud+만료 검증), `build_verifier`, `claims_to_user`(클레임→UserContext 매핑)
- `[Mod] gateway/app/main.py` — `_authenticate`를 Supabase 검증으로 교체, lifespan에서 검증기 생성
- `[Mod] gateway/app/config.py` — `supabase_url`·`supabase_jwks_url`·`supabase_aud` 추가, 라우트·`PUBLIC_PATHS`에서 `/auth` 제거
- `[Mod] libs/common/common/security.py` — 죽은 자체-JWT 함수(`create_token`·`decode_token`)·`import jwt` 제거 (HMAC·UserContext 유지)
- `[Del] services/auth/` — 자체 로그인 서비스 제거
- `[New] libs/common/tests/test_supabase_auth.py` — 자체 RSA 키로 JWKS 시뮬레이션 (5 케이스)

**DB**
- `[Mod] infra/db/init/01-create-databases.sql` — `auth_db` 제거(Supabase가 계정 소유)

**설정**
- `[Mod] docker-compose.yml` — `auth` 서비스·gateway depends_on 제거
- `[Mod] .env.example` — `SUPABASE_URL`·`SUPABASE_JWKS_URL`·`SUPABASE_AUD` 추가, 자체 JWT 키 제거
- `[Mod] README.md` — 저장 표(Supabase 외부), 로그인 안내(Supabase 발급)

## API 변경

- **제거**: `POST /auth/login`, `POST /auth/refresh` (Supabase가 대체)
- **인증 흐름**: 클라이언트가 Supabase로 로그인 → access token을 게이트웨이에 `Bearer`로 전달 → 게이트웨이 JWKS 검증
- 계약: `doc/design/auth/api-contract.py` (mypy --strict 통과)

## 검증

- 단위 테스트 `test_supabase_auth.py` — 5 pass(유효·이메일 폴백·잘못된 aud·만료·위조 서명)
- mypy --strict — supabase_auth·security·gateway 4파일 clean
- 잔여 참조 grep 0 (auth 서비스·decode_token·create_token)

## 특이사항 (설계 대비·제약·후속)

- **이탈(Deviation)**: `security.py`의 `create_token`·`decode_token`은 File Map에 없었으나 auth 제거로 죽은 코드가 되어 제거(ADR 0007이 대체). History 기록.
- **코드↔계약 불일치(리포트)**: 계약의 `AuthError` 레지스트리(`AUTH001~005`)를 구현이 아직 쓰지 않고 기존 `AppError("unauthorized"/"forbidden", …)` 코드를 그대로 사용. **후속**: 게이트웨이·검증기에서 `AuthError` 코드로 통일 필요(계약을 덮어쓰지 않고 코드 정정 권장).
- **사람 게이트**: 실제 Supabase 프로젝트 생성 + `.env`의 `SUPABASE_*` 채우기. 그 전엔 게이트웨이 e2e 불가(단위 검증까지 완료).
- **AC2 e2e**: 게이트웨이→하류 HMAC 전달은 원형 패턴 유지라 배선 안전하나, 실행 서버 e2e는 미수행.
