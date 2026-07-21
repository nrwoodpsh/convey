# task-issue-detector-20260720.md

> 라운드 ② (이슈 선별, 알파2). 계약 정본 = `api-contract.py`. 자연어 설계만.

## 1. Requirements

- **Scenario**: `market.ticks`(시세)·`research.ingested`(뉴스) 스트림이 흐른다. `issue-detector`가 이를 집계해 "**오늘 뭘 만들지**"를 랭킹으로 뽑고, 사람이 `GET /issues/today`로 확인 후 `POST /content/generate`로 선택한다.
- **Objective**: 시세 급변 + 뉴스 빈도로 **이슈 종목을 자동 포착**한다(편집 신호). 콘텐츠를 자동 유발하지 않고 사람 선택으로 넘긴다.
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract.py`가 contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: 랭킹 점수 = 등락률·거래량 z-score·뉴스빈도의 **가중합**이며 가중치·윈도우가 설정값
  - [ ] AC3: `GET /issues/today`가 top_k 이슈 종목을 **score 내림차순**으로 반환
  - [ ] AC4: research/content **DB 직접접속 없음** — Kafka 스트림만 소비(경계 유지)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - `issue-detector` 서비스 없음(신규). `market-feed` 골격 참고.
  - 스트림 집계 상태(윈도우별 카운트·시세)를 **어디에 두나** — 외부 DB 금지(경계). 프로세스 내 메모리(재기동 시 윈도우 재구축) or 자체 경량 저장.
  - 거래량 z-score엔 **기준 통계**(평균·표준편차)가 필요 — 초기 데이터 부족 시 급증 판정 왜곡.
- **핵심 결정**:
  - **결정 1 — 출력 형태**: 택함 = **조회 API `GET /issues/today`**(워커 + 얇은 API) / 기각 = `issue.detected` 이벤트 / 사유 = 아키텍처상 랭킹은 "조회 상태"(자동 유발 X, 사람 선택)
  - **결정 2 — 집계 상태 위치**: 택함 = **프로세스 내 롤링 윈도우**(POC) / 기각 = 별도 DB / 사유 = DB 경계 유지·단순. 재기동 시 윈도우 재구축 허용
  - **결정 3 — 점수식**: 택함 = **가중합**(w_change·w_volume·w_news 설정) / 기각 = 학습 모델 / 사유 = 설명가능·POC 단순. 가중치 튜닝은 운영에서

## 4. Logic

- 소비: `market.ticks` → 종목별 최신 시세·거래량 롤링 갱신 / `research.ingested` → 종목별(`tickers`) 뉴스 카운트 롤링 갱신 (윈도우 `window_hours`)
- 점수: `score = w_change*|등락률| + w_volume*volume_z + w_news*news_count`
- `GET /issues/today`: 현재 윈도우 스냅샷 → score 내림차순 top_k → `IssueRankItem[]`
- 거래량 z-score: 종목별 롤링 평균·표준편차 기준. 데이터 부족 시 0 처리(보수적).

## 6. File Map (기계적)

- `[New] doc/design/issue-detector/api-contract.py` — 계약 (작성 완료·mypy 통과)
- `[New] services/issue-detector/app/worker.py` — 두 토픽 소비 + 롤링 집계 (market-feed 골격 참고)
- `[New] services/issue-detector/app/ranking.py` — 점수식·윈도우
- `[New] services/issue-detector/app/main.py` — 얇은 조회 API `GET /issues/today`
- `[Mod] gateway/app/config.py` — `/issues` 라우트 등록
- `[Mod] docker-compose.yml` — `issue-detector` 서비스 추가(kafka depends_on)

## 7. Verification

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(`/builder`): 모의 틱·뉴스 투입 → `/issues/today`가 score 내림차순 반환(AC2·AC3), DB 접속 코드 grep 0(AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260720 | /design | 최초 설계 — 워커+조회API, 가중합 랭킹 (알파2) |
| 20260720 | /builder | `RollingRanker`(가중합·롤링윈도우) + worker(두 스트림 소비) + main(`GET /issues/today`) 구현. gateway `/issues`·compose 등록. **랭킹 결정론 단위 4 pass**(정렬·윈도우·z-score)·mypy clean. 스트림 소비·API는 구조적 배선(Kafka e2e 후속). |
| 20260721 | /builder(실 스트림 e2e) | **실 Kafka 스트림 관통 검증**(코드 변경 없음). 실 KRX ticks(005930/000660/035420) + 실 RSS 뉴스(035420 태깅)를 발행 → worker가 새 그룹으로 전부 소비(earliest) → `RollingRanker`. 랭킹(24h): ①005930 등락 +2.62%·vol_z 1.0, ②035420 news=2. **윈도우 필터 정확**(005930 뉴스는 24h 밖=0, 720h=1). "Kafka e2e 후속" 해소. |
