# 20260723 — 요약: 확장 Phase E (데이터 — 종목 마스터·수집 확대·그래프 사건)

- **Task**: `doc/design/content/20260723-task-expansion.md` (라운드㉙ · Phase E)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: Phase E 완료·검증. 종목 20→46, 수집 소스 확대, 그래프 관계 7→54. (F 안정은 후속)

## 변경사항

- **E1 종목 마스터**: `scripts/gen-stocks.py`(신규) — pykrx로 KOSPI 상위 ticker→명을 뽑아 `common/stocks.py`의 `# <gen:names>` 마커 사이를 재생성(정적 커밋). 현재 env는 미래 날짜라 pykrx 라이브 조회 불가 → **큐레이션으로 종목 20→46·`STOCK_SECTOR` 확대**(스크립트는 실배포용).
- **E2 수집 확대**: `market-feed` symbols 3→16(주요종목), `news-feed` `feed_urls` 2→5(연합·한경·매경·이데일리·서울경제).
- **E3 그래프 사건 + 오탐 수정**:
  - `research/consumer.py` — `event_hints`(실적·공시·급등락)로 종목→**HAS_EVENT** 결정론 엣지(근거=article) 추가. `_STOCK_NAMES_SET`로 종목 판정.
  - `news-feed/tagging.py` — `_suppress_substrings`: 짧은 종목명(SK·LG)이 긴 이름(SK하이닉스)에 포함될 때 제거(오탐 방지).
  - `research/backfill.py` — `--llm`/`--limit`: 과거 기사 본문에 `extract_relations`(Ollama) 재실행(일회성·재개).

## API/타입 변경

- 없음(데이터·태깅·그래프 로직). 계약 `api-contract-expansion.py`.

## 검증 (실 컨테이너 스택)

- E1: `stock_name` — 015760 한국전력·017670 SK텔레콤·036570 엔씨소프트(신규).
- E2: news-feed `feeds=5`, `research.ingested 329건`.
- E3: 그래프 관계 **7→54**(BELONGS_TO 24·AFFECTS 13·COMPETES 8·HAS_EVENT 5·SUPPLIES 4). news-feed 단위테스트 6 통과(부분문자열 수정 포함).

## 특이사항 (설계 대비·후속)

- **이탈**: (1) pykrx 라이브 생성은 **미래-날짜 시뮬 env**로 KRX 빈 응답 → 큐레이션 확대로 성과 달성(스크립트 커밋, 실배포 날짜엔 정상). (2) 결정론 HAS_EVENT는 기사 event 키워드 의존이라 희소 — DART 공시 유입 시 증가(현 HAS_EVENT 5는 LLM+결정론 혼재). (3) `backfill --llm`은 Ollama로 느려 백그라운드 실행(무오류 시작).
- 섹터 자동 분류는 pykrx 미지원 → `STOCK_SECTOR` 수기 유지(후속: KRX 업종 매핑).
- **다음**: Phase F(합성 재시도·자동양산 검증·/ui/stats 모니터링).
- 커밋: 아직(사람 게이트 — `/commit`).