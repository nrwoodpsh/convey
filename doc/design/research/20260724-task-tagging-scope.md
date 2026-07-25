# 20260724-task-tagging-scope.md

> 라운드 ㉜ (종목·엔티티 태깅 오탐 완화 — 제목 우선 + 본문 조건).
> 계약: `api-contract-tagging.py`. 도메인 research(수집·태깅). tagging.py는 news-feed 서비스. 결정론(LLM 미사용).

## 1. Requirements

- **문제(검증됨)**: `tag_tickers`가 **제목+본문 전체에 단순 부분문자열**(`name in text`)로 종목명을 매칭 → 본문에 스쳐 지나가는 종목명까지 태깅. 실측 오탐:
  - "경동나비엔 보일러 A/S" → 본문 "**카카오**톡 채널" → 카카오(035720) 오태깅.
  - "이마트 빙수 밀키트" → 본문 "저당**카카오**"(초콜릿 원두) → 카카오 오태깅.
  - 공통: **제목엔 종목명 없음, 본문에만 1회 스침.**
- **원인(정정)**: `body`는 페이지 전체 스크랩이 아니라 **피드 요약/발췌**(RSS summary·Naver description·DART report_nm) — 페이지 잡음이 원인이 아님. 진짜 원인 = ① **매칭 범위**가 제목+본문 전체(본문 스침 포함) + ② **bare substring**(문맥·동음이의 무시).
- **영향**: 틀린 ticker → 그래프에 틀린 종목→섹터/사건 엣지·틀린 기사 회수 → 알파①(정확·근거) 훼손. 엔티티(`tag_entity_names`)도 같은 메커니즘이라 그래프 seed 오탐으로 전파.
- **목표**: **제목에 있으면 확정 태깅, 본문에만 있으면 등장 횟수 조건**(제목 우선 + 본문 조건)으로 스침 오탐 제거. 결정론·사전 밖 태깅 0 불변.
- **Acceptance Criteria**:
  - [x] AC1: **제목**에 종목명 → 태깅. 검증: 단위("현대차 노조 파업" 제목 → 005380).
  - [x] AC2: **본문 1회 스침** → 태깅 안 함. 검증: 단위("경동나비엔…" 본문 "카카오톡" 1회 → 035720 없음; "이마트 빙수" 본문 "저당카카오" → 없음).
  - [x] AC3: **본문 ≥ BODY_MIN_MENTIONS(2)회** 실질 언급 → 태깅. 검증: 단위(본문에 종목명 2회, 제목 없음 → 태깅).
  - [x] AC4: **회귀 없음** — 기존 태깅 테스트(SK↔SK하이닉스 억제, 사전 밖 제외 등) 통과, `tag_entity_names`도 동일 규칙 적용. mypy·계약 통과.
  - [x] AC5: 가드레일 불변 — 사전 밖 태깅 0(환각 방지), LLM 미사용(결정론).

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**(사용자 확정):
  - **결정 1 — 접근**: 택함 = **제목 우선 + 본문 조건(횟수)** / 기각 = 동음이의 예외목록(새 패턴마다 수동·유지비↑) / 기각 = 문맥 ML(과함·결정론 위배) / 사유 = 오탐 대부분이 "제목엔 없고 본문 1회 스침"이라 범위·횟수 규칙으로 값싸게 제거. (사용자 확정)
  - **결정 2 — 엔티티도 적용**: 택함 = `tag_entity_names`도 동일 규칙 / 사유 = 그래프 seed 오탐 동일 차단(일관성).
- **사각지대**:
  - **시그니처 변경**: `tag_tickers(text)` → `tag_tickers(title, body)`. 호출부(worker.py 2곳)·기존 테스트(`test_tagging.py`) 갱신 필요. 테스트는 **의도 보존하며 새 시그니처로**(약화 아님).
  - **기존 데이터**: 이미 저장된 2,898건 articles.tickers + 그래프 엣지엔 오태깅이 남아있음 → **이번 범위는 신규 수집부터 교정**. 기존 재태깅·그래프 정리는 **후속(별도 스크립트)**. (신규가 쌓이며 자연 개선 + 필요 시 재태깅 배치.)
  - **휴리스틱 한계(정직)**: 본문에 "카카오톡"이 2회 이상 나오는 메시징 기사는 여전히 카카오로 태깅될 수 있음(횟수 규칙의 한계). 제목 우선이 대부분을 거르지만 완벽하진 않음 — 관측 후 필요하면 동음이의 예외를 보강(결정 1의 기각안을 후속 보완으로).
  - **event_hints**: 단순 힌트라 변경 안 함(결합 텍스트 유지).
  - **제목 없는 실질 기사**: 제목에 종목명이 없어도 본문에서 깊게 다루는 기사는 본문 ≥2회로 살림(AC3).

## 3. UI/UX
- 화면 변화 없음(백엔드 태깅 품질). 결과: 그래프의 종목 노드·엣지 정확도↑ → 시나리오·회수 정확도 개선(간접).

## 4. Logic
- **tagging.py**:
  - 상수 `BODY_MIN_MENTIONS = 2`.
  - `_tag_names(title, body, candidates) -> list[str]`(공유):
    - `title_hit = [n for n in candidates if n in title]`
    - `body_hit = [n for n in candidates if n not in title and body.count(n) >= BODY_MIN_MENTIONS]`
    - `_suppress_substrings(title_hit + body_hit)` (이름-내-이름 억제 유지) → 반환.
  - `tag_tickers(title, body, dictionary=None)`: `_tag_names`로 이름 매칭 → dict로 ticker 변환(등장 순서·중복 제거).
  - `tag_entity_names(title, body, names=None)`: `_tag_names(title, body, ENTITY_NAMES)`.
  - `tag_event_hints`: 그대로.
- **worker.py `_news_loop`**: `text = title+" "+body` 결합 제거 → `tag_tickers(doc["title"], doc["body"])`·`tag_entity_names(doc["title"], doc["body"])`로 분리 전달. `tag_event_hints`는 결합 텍스트 유지 가능.

## 5. Implementation Split (다음 /builder)
- tagging.py: `_tag_names`·`BODY_MIN_MENTIONS` 신설, `tag_tickers`·`tag_entity_names` 시그니처·로직 교체.
- worker.py: 호출부 2곳 title/body 분리.
- test_tagging.py: 기존 케이스 새 시그니처로 갱신 + AC 신규 테스트(제목/본문1회/본문2회).

## 6. File Map (기계적)
- `[Mod] services/news-feed/app/tagging.py` — `_tag_names`·`BODY_MIN_MENTIONS`·`tag_tickers(title,body)`·`tag_entity_names(title,body)`
- `[Mod] services/news-feed/app/worker.py` — 태깅 호출부 title/body 분리
- `[Mod] services/news-feed/tests/test_tagging.py` — 시그니처 갱신 + 오탐/회귀 테스트
- `[New] doc/design/research/api-contract-tagging.py`

## 7. Verification (다음 /builder)
- 단위(`test_tagging.py`):
  - AC1 제목 매칭 태깅 / AC2 본문 1회 미태깅(카카오톡·저당카카오) / AC3 본문 2회 태깅 / AC4 회귀(SK↔SK하이닉스·사전밖 제외).
- 통합(실 스택): 재빌드 후 신규 수집 관찰 — 035720(카카오) 오태깅 신규 발생 감소(로그/DB 표본).
- 가드레일: 사전 밖 태깅 0, LLM 미사용. mypy·계약 통과.

## 8. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /builder | 구현·검증. `tagging.py`: `BODY_MIN_MENTIONS=2`·`_tag_names(title,body,candidates)`(제목 우선+본문≥2회)·`tag_tickers(title,body)`·`tag_entity_names(title,body)`. `worker.py` 호출부 title/body 분리(event_hints는 결합 유지). **검증**: 단위 10/10(카카오톡 1회→미태깅·본문2회→태깅·제목매칭·SK⊂SK하이닉스 억제 회귀), mypy strict 0, 호출부 전수(worker.py만)—영향 0. 로직 결정론이라 단위테스트가 오탐 직접 증명. 실스택 반영은 news-feed 재빌드(배포 단계). |
| 20260724 | /design | 종목·엔티티 태깅 오탐 완화. **검증으로 발견**: 본문 스침(카카오톡·저당카카오) 오태깅(제목엔 없음). 원인 정정(페이지 스크랩 아님 — 매칭 범위+substring). 결정: **제목 우선 + 본문 ≥2회**(예외목록·ML 기각). `tag_entity_names`도 적용. 시그니처 `tag_tickers(title,body)`로 변경(호출부·테스트 갱신). 기존 데이터 재태깅은 후속. 계약 `api-contract-tagging.py` mypy 통과. |
