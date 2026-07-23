# 20260723 — 요약: 확장 Phase F (안정 — 재시도·자동양산 검증·모니터링)

- **Task**: `doc/design/content/20260723-task-expansion.md` (라운드㉙ · Phase F, 마지막)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: Phase F 완료·검증. 재시도·모니터링 추가, 자동양산 무정지 확인. **확장 프로그램(D·E·F) 완결.**

## 변경사항 (content)

- **F1 재시도**:
  - `consumer.handle_generate` — agent 스크립트 호출을 상한(retry_max=2)·백오프로 인라인 재시도(일시 LLM 실패 흡수).
  - `consumer._retry_assemble` — 합성 실패(content.assembled ok=False) 시 `GenerationJob.retry_count`<상한이면 chart+script로 media.assemble **재발행**(멱등, 같은 job). 초과 시 failed.
  - `models.py` + alembic `d2e3f4a50012` — `retry_count` 컬럼.
  - `config.py` — `retry_max`·`retry_backoff_sec`.
- **F3 모니터링**: `repository.stats`(상태별 count + 최근 실패), `GET /ui/stats`(`UiStatsRes`), 대시보드 statsbar 카드(상태별 수 + 최근 실패 토픽).

## API/타입 변경

- 신규: `GET /ui/stats` → `UiStatsRes{by_status, recent_failed}`. `media.assemble`·기타 불변. 마이그레이션 1(retry_count).

## 검증 (실 컨테이너 스택)

- F1: `retry_count` 컬럼 적용. 재시도 기전 구현, 정상 흐름 무영향.
- F2: issue.selected(기아 000270) → 자동 job#38 `scripting→assembling`(scenario_ready·승인 없이 자동 진행 — 알파4 무정지 확인).
- F3: `/ui/stats` → by_status{ready 23·failed 9·assembling·scenario_ready 3·…}·recent_failed(토픽·에러). 대시보드 카드 표시.

## 특이사항 (설계 대비·후속)

- **이탈**: 재시도가 4xx(무티커 422 등 **영구 실패**)도 재시도(낭비) → 5xx/timeout 한정은 후속. 합성 재시도 시 배경은 real 기본(anim 선택 유실 — job에 미저장). 자동 job#38 assembling이 긴 건 D 배경 클립(대용량) 다운로드 영향.
- **확장 프로그램(㉙) 완결**: D(배경 컷)·E(데이터)·F(안정). 남은 것은 C(배포·YouTube 자동·Supabase)뿐.
- 커밋: 아직(사람 게이트 — `/commit`).