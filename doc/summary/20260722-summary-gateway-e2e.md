# 20260722 — 요약: 게이트웨이 경유 e2e 검증 + 프리픽스 버그 수정 (B1)

- **Task**: `doc/design/infra/task-gateway-e2e-20260722.md` (라운드⑰, 인프라·보안, ADR 0007)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 gateway·content·로컬 JWKS)
- **상태**: 게이트웨이 인증·프록시 경로 최초 관통 검증. **검증 중 잠재 버그 발견·수정**. 5개 AC 충족.

## 개요

지금까지 e2e는 서비스를 직접 호출해 **게이트웨이 프록시 경로는 한 번도 관통된 적이 없었다**. 로컬 JWKS 시뮬레이션(자체 RSA 키·JWKS·토큰)으로 gateway를 실검증하다가 **프리픽스 스트립 버그**를 발견해 수정했다.

## 발견·수정 (버그)

- **버그**: gateway `_resolve`가 route prefix를 제거(`/content/generate` → `/generate`)해 프록시하는데, 하류 도메인 라우터는 prefix(`/content`)를 그대로 써서 **모든 프록시 경로가 404**. 또한 HMAC 서명 경로가 하류 `url.path`와 불일치(403 위험). py-msa-ai 원형의 잠재 결함.
- **수정**: `_resolve`가 **prefix를 제거하지 않고 전체 경로를 프록시**(`base + /content/generate`). HMAC 서명 경로도 전체 경로 → 하류와 일치. gateway 1개 함수 수정으로 모든 라우트 일괄 해결.

## 변경사항

- `gateway/app/main.py` — `_resolve`: prefix 제거 → **전체 경로 유지**.

## 검증 (실 gateway·content·로컬 JWKS)

- 로컬 RSA 키페어 → JWKS(http.server 서빙) → 토큰 4종(유효·잘못 aud·잘못 iss·다른키 위조).
- **AC1**: 유효 토큰 → `POST gateway/content/generate` → **202 {job_id}** + content_db 잡 생성(**owner_id=JWT sub=tester**, 신뢰헤더 정상).
- **AC2**: 무토큰 → 401(AUTH001).
- **AC3**: 위조(다른키)·잘못 aud·잘못 iss → 각각 401.
- **AC4(보안)**: 클라이언트가 `X-User-Id: hacker`+가짜 서명헤더 첨부해도 → **스트립**되고 잡 owner=tester(gateway 서명본이 이김).
- **AC5**: mypy --strict clean.

## 특이사항 (후속)

- **B1의 소득**: 검증 라운드로 시작했으나 실제 버그를 잡아 수정. 게이트웨이 프록시가 이제 실제로 동작.
- 인증은 **로컬 JWKS 시뮬**으로 검증(실 Supabase는 C2 보류). 프로덕션은 `SUPABASE_*`만 채우면 동일 경로.
- 커밋: 아직(사람 게이트 — `/commit`).
