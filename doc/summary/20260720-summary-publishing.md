# 20260720 — 요약: publishing 라운드⑤ (알파4)

- **Task**: `doc/design/publishing/task-publishing-20260720.md` (ADR 0003)
- **작업**: /run(builder) · 2026-07-20 · main · **로컬 전용**
- **상태**: 멱등 발행 상태머신(알파4 핵심) 검증. YouTube 업로드·스케줄·전송 e2e 남음.

## 개요

승인 완성본(`content.approved`)을 YouTube에 발행. **멱등 상태머신**(content_id 유니크)으로 아웃박스 유실 시에도 **중복 업로드 방지**(알파4: 양산 신뢰성). 발행은 **사람 승인 후에만**(가드레일).

## 변경사항 (BE, 신규 서비스)

- `services/publishing/app/models.py` — `PublishRecord`(content_id 유니크 멱등키, status)
- `services/publishing/app/service.py` — `enqueue`(멱등)·`mark_published/failed`·`get_status`
- `services/publishing/app/youtube.py` — YouTube 부패방지 계층(OAuth 토큰 .env, 업로드 스텁)
- `services/publishing/app/consumer.py` — content.approved → enqueue → 업로드
- `services/publishing/app/{main,config,db,schemas}.py`
- `services/publishing/{pyproject.toml,Dockerfile}`
- `gateway/app/config.py` `/publishing` · `docker-compose.yml` publishing 서비스 · `infra` publishing_db

## 검증 (실서비스·로컬)

- **실 publishing_db**: `enqueue(42)` 2회 → 레코드 **1개**(중복 업로드 방지) · `queued→published` · 조회
- mypy --strict clean · compile OK · compose(16 서비스)·라우트 `/publishing`

## 특이사항 (후속)

- **남음**: YouTube OAuth 업로드(youtube.py 부패방지 실연결, 토큰은 발행 승인 게이트), content.approved 전송 e2e(Kafka), 스케줄 워커(재시도·양산 큐).
- 멱등·상태머신(핵심)은 검증됨. 발행은 사람 승인(content.approved) 후에만 — 가드레일 준수.
