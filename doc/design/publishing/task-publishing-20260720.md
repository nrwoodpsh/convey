# task-publishing-20260720.md

> 라운드 ⑤ (발행·양산, 알파4 + 커모디티). 계약 정본 = `api-contract.py`. 자연어 설계만.

## 1. Requirements

- **Scenario**: 사람이 완성본을 승인(`content.approved`)하면 `publishing`이 YouTube Shorts에 업로드한다. 양산은 스케줄·잡 재개로 안정화한다.
- **Objective**: **사람 승인 후에만** 외부 발행(가드레일). 잡 재개·스케줄로 하루 N개 안정 양산(알파4).
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract.py`가 contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: `content.approved`를 받은 콘텐츠만 업로드 — 미승인 업로드 시 `NOT_APPROVED`(409)
  - [ ] AC3: 업로드 성공 시 `content.published`(external_url 포함) 발행
  - [ ] AC4: 잡 실패 시 상태 기반 **재시도/재개** 가능(간이 아웃박스 유실 보완)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - YouTube OAuth 토큰 수명·갱신. `.env` 주입, 승인 워크플로우 통과 후에만 사용.
  - 간이 아웃박스는 유실 가능 — 발행 같은 부작용은 **멱등키**로 중복 업로드 방지 필요.
- **핵심 결정**:
  - **결정 1 — 발행 트리거**: 택함 = **사람 승인(`content.approved`) 후에만** / 기각 = 자동 발행 / 사유 = 가드레일(콘텐츠 자동발행 금지)
  - **결정 2 — 양산 신뢰성**: 택함 = **잡 상태머신 기반 재개 + 멱등키** / 기각 = 간이 아웃박스만 / 사유 = 유실 시 중복·누락 방지(알파4)
  - **결정 3 — 스케줄**: 택함 = 스케줄 워커가 승인 대기·재시도 큐 처리 / 기각 = 수동 / 사유 = 양산 자동화

## 4. Logic

1. `publishing` consumer: `content.approved` 수신 → PublishStatus=queued
2. YouTube 업로드(부패방지 계층, OAuth) — **멱등키**(content_id)로 중복 방지 → uploading→published
3. 성공 → `content.published`(external_url) 발행 / 실패 → failed, 재시도 큐
4. `GET /publishing/{content_id}` 상태 조회
5. 스케줄 워커: 재시도·양산 큐 주기 처리

## 6. File Map (기계적)

- `[New] doc/design/publishing/api-contract.py` — 계약 (작성 완료·mypy 통과)
- `[New] services/publishing/` — API(상태조회) + consumer(content.approved) + YouTube 래퍼(부패방지 계층)
- `[New] infra/db/init` — `publishing_db` 추가(CREATE DATABASE)
- `[Mod] gateway/app/config.py` — `/publishing` 라우트
- `[Mod] docker-compose.yml` — publishing 서비스, 스케줄 워커
- `[Mod] .env.example` — YouTube OAuth 토큰(이름만)
- `[Mod] services/content/` — 잡 재개 로직(상태머신)

## 7. Verification

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(`/builder`): 미승인 업로드 시도 409(AC2), 승인본 업로드 후 content.published 발행(AC3), 재시도 시 중복 업로드 없음(AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260720 | /design | 최초 설계 — 승인 후 발행·멱등 재개·스케줄 (알파4) |
