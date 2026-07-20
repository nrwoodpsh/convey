# task-auth-supabase-20260719.md

> 라운드 0 (기반·인증). 원형 자체 JWT 발급/검증 → **Supabase Auth 위임**(ADR 0007).
> 계약 정본 = `api-contract.py`. 여기엔 자연어 설계만.

## 1. Requirements

- **Scenario**: 사용자가 Supabase로 로그인해 받은 access token으로 게이트웨이 뒤 API를 호출한다. 게이트웨이가 그 토큰을 검증한다.
- **Objective**: 원형의 자체 JWT 발급·검증을 Supabase에 위임한다. 인증 유지보수를 없애고, 하류 HMAC 신뢰헤더 패턴은 그대로 둔다.
- **Acceptance Criteria**:
  - [x] AC1: 위조·만료·잘못된 aud 토큰 → 401 (단위 테스트 검증). 게이트웨이 e2e는 실행 서버 필요
  - [x] AC2: `sub→user_id`·roles·name 매핑 단위 테스트 통과. HMAC 주입 배선은 원형 패턴 유지
  - [x] AC3: `services/auth` 제거, gateway `decode_token` 제거, `create_token`/`decode_token` 죽은코드 제거 — grep 0
  - [x] AC4: `api-contract.py` contract-gate(`mypy --strict`) 통과
  - [x] AC5: `PUBLIC_PATHS`={/health}, 라우트에서 `/auth` 제거

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대(부딪히면 배울 함정)**:
  - 게이트웨이 `_authenticate`는 **HS256 공유 시크릿**을 가정한다(`decode_token(secret=jwt_secret)`). Supabase 비대칭(JWKS) 전환 시 이 함수를 통째로 교체해야 한다. `common.security.decode_token`은 대칭 전용 → **JWKS 검증 함수 신설**.
  - `sub`가 Supabase에선 **UUID 문자열**(원형 데모는 username). 하류가 user_id를 정수로 가정하지 않는지 확인 — 현재 전부 문자열이라 안전.
  - Supabase 기본 토큰엔 **앱 역할이 없다**(`role`=authenticated만). 역할이 필요하면 `app_metadata` 또는 커스텀 클레임(Access Token Hook) 설정이 선행돼야 한다.
- **핵심 결정**(택한 안 + 기각한 대안):
  - **결정 1 — 검증 방식**: 택함 = **JWKS(비대칭)** / 기각 = HS256 공유 시크릿(간단하나 시크릿을 양쪽에 보관·로테이션 취약) / 사유 = 보안·키 로테이션. *(POC가 급하면 HS256도 가능 — 그 경우 History에 이탈 기록)*
  - **결정 2 — 로그인 위치**: 택함 = **클라이언트가 Supabase에 직접 로그인** → 토큰만 게이트웨이로 / 기각 = 게이트웨이 로그인 프록시 / 사유 = Supabase가 소유, 우리 표면 최소화
  - **결정 3 — auth 서비스**: 택함 = **제거**(`auth_db` 포함) / 기각 = 프로필 래퍼 유지 / 사유 = POC엔 프로필 확장 불필요. 필요해지면 별도로 승격

## 4. Logic

게이트웨이 검증 흐름:
1. Bearer 토큰 추출
2. **JWKS(캐시)로 서명 검증** + `aud=authenticated` + `exp` 확인
3. 실패 → `AuthError`(401)
4. claims → `GatewayUserContext`: `sub→user_id` · `user_metadata.name`(없으면 email)→user_name · `app_metadata.roles`(CSV)→roles
5. 기존대로 `sign_internal`로 HMAC 신뢰헤더 부착 (원형 하류 패턴 불변)

JWKS는 앱 기동 시/주기적으로 캐시한다. `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.

## 6. File Map (기계적)

- `[Mod] gateway/app/main.py` — `_authenticate`를 Supabase JWKS 검증으로 교체, claims 매핑
- `[New] libs/common/common/supabase_auth.py` — JWKS 캐시 + `verify_supabase_jwt(token) → claims`
- `[Mod] gateway/app/config.py` — `supabase_url`·`jwks_url`·`aud` 추가, `routes`/`PUBLIC_PATHS`에서 `/auth` 정리
- `[Del] services/auth/` — 서비스 제거 (필요 시 프로필 래퍼로 축소)
- `[Mod] infra/db/init/01-create-databases.sql` — `auth_db` 제거
- `[Mod] docker-compose.yml` — `auth` 서비스 제거, `gateway` depends_on 조정
- `[Mod] .env.example` — `SUPABASE_URL`·`SUPABASE_JWKS_URL`·`SUPABASE_AUD` 추가, `JWT_SECRET` 제거(`GATEWAY_INTERNAL_SECRET` 유지)
- `[New] doc/design/auth/api-contract.py` — 클레임·매핑·에러 계약 (작성 완료)

## 7. Verification

- 명령: `python -m mypy --strict --ignore-missing-imports doc/design/auth/api-contract.py`
- 통과 조건: Exit 0 (AC4). ✅ 통과 확인.
- 구현 후: 실제 Supabase 토큰 → 200, 위조 토큰 → 401 (`/builder` tdd-verify로 AC1·AC2)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260719 | /design | 최초 설계 (ADR 0007 — Supabase 인증) |
| 20260720 | /builder | `supabase_auth.py`(JWKS 검증+매핑) 신설, gateway `_authenticate` 교체, `services/auth`·`auth_db` 제거, compose·infra·.env·README 정리. 단위 테스트 5 pass, mypy --strict 4파일 clean |
| 20260720 | /builder · Deviation | 계획: File Map에 `security.py` 미언급 / 코드: `create_token`·`decode_token`(자체 JWT)이 auth 제거로 죽은 코드 + mypy 에러 노출 / 선택: 두 함수·`import jwt` 제거 / 사유: ADR 0007이 대체하는 함수라 auth 마이그레이션의 마무리 |
