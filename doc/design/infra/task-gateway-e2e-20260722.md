# task-gateway-e2e-20260722.md

> 라운드 ⑰ (B1 — 게이트웨이 경유 e2e 검증). 인프라·보안. ADR 0007.
> 계약 변경 없음. **검증 중심**(gateway 코드는 완성 — 신규 코드 예상 0).

## 1. Requirements

- **결론**: 지금까지 e2e는 서비스/consumer를 **직접** 호출했다. 실제 **게이트웨이(단일 진입 + JWKS 검증 + 신뢰헤더 제거 + HMAC 서명 + 프록시)**를 통과해 `POST /content/generate`가 도는지 미검증. Supabase 미설정이라 **로컬 JWKS 시뮬레이션**으로 인증 경로를 실검증한다(round0 unit의 라이브 확장).
- **Scenario**: 자체 키페어로 JWKS를 서빙하고 토큰을 발급 → gateway가 검증·신뢰헤더 주입·content로 프록시 → 202 + 잡 생성. 무토큰·위조는 401.
- **Objective**: gateway 인증·프록시 경로가 실제로 동작함을 증명(보안 경계 포함).
- **Acceptance Criteria**:
  - [ ] AC1: 로컬 JWKS 시뮬(자체 EC 키·JWKS·토큰)로 gateway가 유효 토큰 검증 → `/content/generate` **202 + 하류 content에 잡 생성**(신뢰헤더 정상)
  - [ ] AC2: **무토큰** → 401(AUTH001)
  - [ ] AC3: **위조 토큰**(다른 키 서명 / 잘못된 aud / 잘못된 iss) → 401
  - [ ] AC4: **클라이언트 위조 신뢰헤더 제거** — 클라이언트가 `X-User-Id` 등을 붙여도 하류엔 gateway 서명본만 도달(스트립 확인)
  - [ ] AC5: (코드 변경 시) mypy — 예상 변경 없음(검증만). 버그 발견 시 정지·수정

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - `PyJWKClient`는 **요청 시점 JWKS fetch**(캐시) → JWKS 서버가 검증 요청 시 살아있어야. gateway 시작 순서 무관.
  - 토큰 요건: `aud=authenticated`, `iss={supabase_url}/auth/v1`, `exp` 유효, alg ES256/RS256(자체 키와 일치).
  - gateway↔content **HMAC 시크릿 일치**(`GATEWAY_INTERNAL_SECRET`) 필요 — 불일치면 하류 403.
  - content는 잡 생성만(202) — agent/파이프라인 불필요(비동기 consumer). gateway+content+JWKS만으로 검증 가능.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 인증 검증 방식**: 택함 = **로컬 JWKS 시뮬레이션**(자체 키페어→JWKS HTTP 서빙→토큰 발급) / 기각 = gateway에 dev-bypass 추가(보안 스멜)·mock 주입(라이브 아님) / 사유 = 실 gateway 코드 그대로 프로덕션 경로 검증. Supabase만 로컬 대체.
  - **결정 2 — 코드 변경**: 택함 = **gateway 코드 무변경**(env 설정만) / 기각 = 테스트용 코드 삽입 / 사유 = gateway는 round0에 완성. B1은 검증.
  - **결정 3 — 범위**: 택함 = **인증(성공/실패) + 스트립 + 프록시 → content 잡 생성** / 기각 = 전체 파이프라인(ready)까지 / 사유 = B1은 "gateway 경유" 자체가 목표. 파이프라인은 별도 e2e에서 검증됨.

## 3. UI/UX
해당 없음.

## 4. Logic (검증 절차)

```
1) 자체 EC(ES256) 키페어 생성 → 공개키를 JWKS(kid 포함)로 → http.server로 서빙(로컬 URL)
2) gateway 기동: SUPABASE_JWKS_URL=로컬JWKS, SUPABASE_URL=http://localhost(→iss),
   SUPABASE_AUD=authenticated, ROUTE_CONTENT=http://localhost:8080, GATEWAY_INTERNAL_SECRET=공유
3) content 기동(8080): DATABASE_URL content_db, KAFKA localhost:29092, 같은 시크릿
4) 토큰 발급(EC 개인키, sub·aud·iss·exp) → POST gateway/content/generate + Bearer
   → 202 {job_id}, content_db에 잡 생성(owner=sub) (AC1)
5) 무토큰 → 401(AC2). 다른키/잘못 aud/iss 토큰 → 401(AC3)
6) 클라이언트가 X-User-Id 위조 헤더 첨부 → 하류엔 gateway 서명 user만(스트립, AC4)
```

## 5. Implementation Split

- **검증 스크립트/절차만**(신규 앱 코드 없음 예상). 로컬 JWKS 서버 + 토큰 발급 + gateway·content 기동 + 요청.
- 버그 발견 시에만 해당 서비스 수정(정지·리포트 후).

## 6. File Map (기계적)

- (예상) 앱 코드 변경 없음. `doc/summary/`에 검증 결과 기록.
- 검증 헬퍼는 scratchpad(비커밋) 또는 필요 시 `scripts/`.

## 7. Verification
- 위 Logic 1~6을 실 gateway·content·로컬 JWKS로 수행. 202·401·스트립 확인.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | gateway 경유 e2e 검증 설계 — 로컬 JWKS 시뮬(자체 키·토큰)로 인증·프록시 실검증. gateway 코드 무변경(검증 라운드). 성공/무토큰/위조/스트립. |
| 20260722 | /builder(버그 발견·정지) | 검증 중 **게이트웨이 프리픽스 스트립 버그** 발견 — `_resolve`가 route prefix를 제거(`/content/generate`→`/generate`)하는데 하류 라우터는 prefix 사용 → **프록시 전 경로 404**(+ HMAC 서명 경로 불일치로 403 위험). py-msa-ai 원형의 잠재 결함, 프록시가 여태 미검증이라 안 드러남. §7대로 정지·리포트·승인 대기. |
| 20260722 | /builder(수정·검증) | 승인 후 **gateway `_resolve` 수정 — prefix 제거 없이 전체 경로 프록시**(base + full path), HMAC 서명 경로도 전체 경로. **실 gateway+content+로컬 JWKS 재검증**: 유효 토큰→**202 + 잡 생성(owner=JWT sub=tester)**(AC1), 무토큰→401(AC2), 위조/잘못 aud·iss→401(AC3), 클라이언트 위조 `X-User-Id: hacker` **스트립**(잡 owner=tester)(AC4), mypy clean(AC5). 게이트웨이 프록시 경로 최초 관통 검증. |
