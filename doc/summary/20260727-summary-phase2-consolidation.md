# 20260727 — 2차 개발 종합 (수렴/정리)

- **작업**: /sync(수렴) · 2026-07-27 · main
- **범위**: 2차 개발 전체 상태 정리 — 로드맵 갱신·㊶ AC 정정·통합 스모크 시나리오·P4·P5 문서 정합.
- **비주얼 리포트**: `claude.ai/code/artifact/a2fa1f6a-ea0a-4c14-b7a2-4b91b52101a6` (repo 밖 아티팩트).

## 개요

2차 개발(상품화 Q·U·C + 학습 트랙 T = Kafka 정석)을 한 바퀴 완주하고 상태를 정리했다. 상품화는 커밋 완료, 학습 트랙은 P1~P3 커밋·P4·P5 커밋 대기, ㊶ 외부 실연결 2건은 2차 점검 후로 예약.

## 완료·검증 (커밋됨)

- **품질**: ㉜ 태깅 · ㊲ 이슈 dedup · ㉟ 온톨로지(노드 9·엣지 12).
- **수집·운영**: ㉝ P1~P4 (admin_db·news-feed·issue-detector 게이팅).
- **제작**: ㊳ 시나리오 템플릿 · ㊴ P1·P2 (배경 라이브러리·생성·가독성 패널).
- **관리화면**: ㊵ P1·P2 (대시보드 설정·근거·지표 백엔드+프런트).
- **인증·발행 코드**: ㊶ (YouTube OAuth 배선·Supabase JWKS 활성·멱등·폴백).
- **이벤트 정석**: ㊱ P1 봉투 · P2 Avro+Schema Registry · P3 Debezium 아웃박스.

## 커밋 대기 (검증 완료, 스테이징)

- **㊱ P4 DLQ+수동커밋** — `consume_reliable`(at-least-once·재시도·`*.dlq`). 라이브 DLQ 도달 확인.
- **㊱ P5 모니터링** — Prometheus·Grafana·kafka-exporter. consumer_lag·dlq_rate 대시보드.

## 미완 — 실 외부연결 (2차 점검 후, [[pending-youtube-supabase]])

| 항목 | 상태 | 막힌 지점 |
|:--|:--|:--|
| YouTube 실 업로드 | 코드 O / 실행 X | `YOUTUBE_REFRESH_TOKEN` 없음(client_id·secret은 있음) → configured=False |
| Supabase 실 인증 | 코드 O / 연결 X | `SUPABASE_URL` placeholder → 게이트웨이가 실 프로젝트 미검증 |
| 대시보드 노출 | 결정대로 | :8091 무인증 로컬(ADR 0010) — 배포 시 게이트웨이 뒤 |

> 정정: ㊶ task 문서 AC1·AC4를 `[x] 완료` → `[~] 코드완료·실연결미완`으로 수정(2026-07-26 정밀 점검).

## 문서 동기화

- `doc/design/20260724-roadmap-phase2.md`: 체크리스트 2~7 구현 ✅, 8 ◐(코드완료·실연결미완), M2/M3/M4 상태 갱신 + 2차 종합 주석.
- `doc/design/publishing/20260725-task-publish-youtube.md`: AC1·AC4 정정.
- `doc/design/eventing/20260725-task-eventing.md`: P4·P5 History·AC 반영(각 라운드 sync).
- `doc/ref/integration-scenario-phase2.md`(신규): 커밋 전 로컬 통합 스모크(8흐름).
- `doc/decisions/0019-eventing-standard.md`: P4·P5 구현 노트.

## 다음 순서

1. 커밋 전 통합 스모크(`doc/ref/integration-scenario-phase2.md`) 로컬 1회.
2. P4·P5 커밋(분리 권장).
3. YouTube refresh_token 획득 스크립트 → 실 업로드 검증.
4. Supabase 프로젝트 생성 → 실 JWKS 검증.

## 특이사항

- ADR README(`doc/decisions/README.md`)는 인덱스 표가 없는 가이드 문서 → 0019 인덱스 갱신 대상 아님(드리프트 아님).
- 커밋: 아직(사람 게이트 — `/commit`). push·merge는 사람이 외부 툴로.
