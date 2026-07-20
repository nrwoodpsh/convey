# 20260720 — 요약: issue-detector 라운드② (알파2)

- **Task**: `doc/design/issue-detector/task-issue-detector-20260720.md` (ADR 0004)
- **작업**: /run(builder) · 2026-07-20 · main · **로컬 전용**
- **상태**: 랭킹 코어 검증. 스트림 소비·API는 구조적 배선(Kafka e2e 후속).

## 개요

시세 급변 + 뉴스 빈도로 "오늘의 이슈 종목"을 자동 랭킹(알파2). `market.ticks`·`research.ingested` 스트림을 **프로세스 내 롤링 윈도우**로 집계(DB 직접접속 없음 — 경계 유지), `GET /issues/today`로 노출(조회 상태, 이벤트 아님).

## 변경사항 (BE, 신규 서비스)

- `services/issue-detector/app/ranking.py` — `RollingRanker`: `score = w_change*|등락률| + w_volume*volume_z + w_news*news_count`
- `services/issue-detector/app/worker.py` — 두 스트림 동시 소비 → 랭커 갱신
- `services/issue-detector/app/main.py` — `GET /issues/today`(워커 백그라운드 + 조회 API 동거)
- `services/issue-detector/{config.py,pyproject.toml,Dockerfile}`
- `gateway/app/config.py` — `/issues` 라우트
- `docker-compose.yml` — issue-detector 서비스

## 검증

- **랭킹 결정론 단위 4 pass**: score 내림차순 정렬, 뉴스 윈도우 경계, 오래된 틱 제외, 거래량 급증 양의 z-score
- mypy --strict clean · compile OK · compose 유효(14 서비스) · 라우트 `/issues` 확인

## 특이사항 (후속)

- 스트림 소비(`run_consumers`)·조회 API는 표준 배선 — **Kafka 스트림 e2e는 Kafka 호스트노출 시 검증**. 랭킹 로직(핵심)은 결정론 검증됨.
- 거래량 z-score는 윈도우 내 샘플 2개 미만이면 0(초기 데이터 부족 보수 처리).
- 종목명(name)은 현재 빈값 — 종목 사전/메타 연계는 후속.
