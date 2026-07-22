# task-compose-e2e-20260722.md

> 라운드 ⑱ (B4 — 전체 컨테이너 기동 검증). 인프라. ADR 0006·0008.
> **검증 중심**(코드는 완성 — 빌드 실패 시에만 수정). 라운드⑨ compose 정합의 실기동 확인.

## 1. Requirements

- **결론**: 지금까지 전부 **로컬 프로세스**(PYTHONPATH)로 검증했다. `docker compose`로 **이미지가 빌드되고 스택이 실제로 뜨는지**는 미확인(라운드⑨는 config·publishing 이미지까지만). 전 앱 이미지 빌드 + 기동 + 배선을 실검증한다.
- **Scenario**: `docker compose build` → 전 앱 이미지 성공. `docker compose up` → DB 서비스가 마이그레이션 후 기동, 워커가 Kafka 조인, 게이트웨이 헬스.
- **Objective**: "로컬 프로세스로만 검증"의 마지막 간극 — 컨테이너 재현성 실증.
- **Acceptance Criteria**:
  - [ ] AC1: `docker compose build` — **전 앱 이미지 빌드 성공**(의존성 정합: pykrx·edge-tts·alembic·matplotlib 등)
  - [ ] AC2: `docker compose up -d` → 앱 서비스 **기동**(gateway·research·content·video-assembly·news-feed·issue-detector·market-feed·agent·llm-inference)
  - [ ] AC3: DB 서비스(research·content·publishing) 기동 시 **`alembic upgrade head` 자동 실행**(로그·테이블 확인)
  - [ ] AC4: 워커/소비자가 **Kafka 조인**(로그) — 서비스 간 배선 확인
  - [ ] AC5: (스트레치) 컨테이너 내 generate → 미디어 볼륨에 mp4 (Ollama 네이티브 재사용)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **이미지 ~10개 빌드 = 수 분·네트워크**. pykrx(pandas/numpy)·matplotlib 무겁고, 빌드 실패 여지(Dockerfile/pyproject 의존성).
  - **Ollama**: `.env` `OLLAMA_HOST=host.docker.internal:11434`(네이티브 재사용) — 컨테이너 ollama 미기동. generate 시 이게 닿아야.
  - **gateway 인증**: 실 Supabase 없음 → gateway 경유 generate는 JWKS 토큰 필요(B1처럼). in-container generate는 **content 컨테이너에 직접**(Kafka 경유가 자연) 또는 스킵.
  - **인프라 재사용**: pg·neo4j·kafka는 이미 기동 중 → app만 빌드·업.
  - 빌드 실패는 **실제 결함**일 수 있음(B1처럼) → §7 정지·리포트.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 검증 범위**: 택함 = **빌드(AC1) + 기동(AC2) + 마이그레이션·배선(AC3·AC4)** 필수, **in-container generate는 스트레치(AC5)** / 기각 = 전체 generate 필수 / 사유 = 파이프라인 로직은 로컬 프로세스로 관통 검증됨. B4의 새 신호는 "빌드되고 뜨는가". generate는 ollama·gateway 복잡도 대비 새 신호 적음.
  - **결정 2 — 코드 변경**: 택함 = **무변경 전제, 빌드/기동 실패 시에만 수정**(정지·리포트 후) / 사유 = 검증 라운드.
  - **결정 3 — 기동 대상**: 택함 = **app 서비스만 빌드·업**(인프라는 기존 재사용) / 기각 = 인프라 포함 재기동(데이터·시간) / 사유 = 효율.

## 3. UI/UX
해당 없음.

## 4. Logic (검증 절차)

```
1) docker compose build              # 전 앱 이미지 (AC1) — 실패 시 정지·리포트
2) docker compose up -d <app 서비스>  # 인프라는 기존 (AC2)
3) 로그: research/content/publishing "alembic upgrade head" (AC3)
   워커 "consuming topic=..." Kafka 조인 (AC4)
4) (스트레치) content 컨테이너 경유 generate → media 볼륨 mp4 (AC5)
```

## 5. Implementation Split
- **검증만.** 빌드/기동 실패가 결함을 드러내면 해당 Dockerfile/pyproject/compose 수정(정지·승인 후).

## 6. File Map (기계적)
- (예상) 변경 없음. 실패 시 `services/*/Dockerfile`·`pyproject.toml`·`docker-compose.yml` 중 해당 부분.

## 7. Verification
- 위 Logic 1~4(필수) + 5(스트레치). 이미지 빌드 성공·서비스 기동·마이그레이션·Kafka 조인 확인.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 전체 컨테이너 기동 검증 — 빌드+기동+마이그레이션+Kafka 배선 필수, in-container generate 스트레치. Ollama 네이티브 재사용. 코드 무변경(빌드 실패 시만 수정). |
| 20260722 | /builder(버그 발견·정지) | `docker compose build` 성공(11개), 기동 시 **research·video-assembly 크래시** — **선언 안 된 의존성** 발견: research `neo4j`(주석 처리)·`httpx` 누락, video-assembly `httpx` 누락. 로컬 공유 env엔 다 깔려 은폐, 컨테이너(깨끗한 폐쇄)가 잡음. §7 정지·리포트·승인 대기. |
| 20260722 | /builder(수정·검증) | 승인 후 **pyproject 2건 수정**(research: `neo4j>=5.0`·`httpx>=0.27`, video-assembly: `httpx>=0.27`) → 재빌드 → **전 앱 서비스 running**(AC2). AC1 이미지 11개 빌드. AC3 research_db(bbba385fe7b9)·content_db(7598c32287dd)·publishing_db(ba3a7f7a1796) 버전 head(엔트리포인트 마이그레이션). AC4 research·video-assembly·content·issue-detector Kafka 소비 조인, news-feed·market-feed 실 수집 기동. AC5(in-container generate)는 스트레치 미실행(로컬 e2e로 검증됨). 앱 컨테이너 정리(인프라 유지). |
