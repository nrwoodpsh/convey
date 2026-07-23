# 20260723 — 요약: 품질 향상 Phase A (알파 데이터 복원)

- **Task**: `doc/design/content/20260723-task-quality.md` (라운드㉕ · Phase A)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: Phase A 완료·검증. 그래프 인과가 다시 영상 스크립트·음성에 들어감. (Phase B 문장·C 연출은 후속)

## 개요

1차 영상 품질 저하의 **핵심 원인 = 알파가 코드에서 끊김**: agent `Evidence`에 `relations`가 없어 research `/search`의 그래프 관계를 버리고 있었다. Phase A는 (A1) 관계를 스크립트·음성까지 흘리고, (A2) 사실 중복을 제거하고, (A3) 그래프를 확대·백필해 관계가 실제로 존재하게 했다. ADR 0012(그래프 인과+LLM 편집자).

## 변경사항

- **agent**:
  - `rag/retriever.py` — `Evidence.relations` 추가, `gather`가 `/search`의 relations(무출처 제외) 파싱.
  - `script/builder.py` — `RelationEvidence`·`_relation_sentence`(조사 자동 `_josa`), `build_script(relations)`가 템플릿별 `relation` 섹션 생성(근거=article_id).
  - `main.py` — build_script에 relations 전달. **그래프 조회 entity를 티커코드→종목명**으로 수정(노드가 이름이라 매칭되던 gap).
- **research**:
  - `domains/research/service.py` — 사실 정규화 dedup(중복 헤드라인 병합, 최신순).
  - `graph`/consumer — 결정론적 **종목→섹터 `BELONGS_TO`** 엣지(단일 종목 기사도 그래프에).
  - `app/backfill.py` (신규) — 과거 기사 섹터 엣지 백필.
- **common**: `stocks.py` — 종목 6→20, `STOCK_SECTOR`·`SECTORS`·`ENTITY_NAMES`·`sector_of`.
- **news-feed**: `tagging.py` — 공유 사전 사용, `tag_entity_names` allow-list = 종목+섹터.
- **content**: `media.py` `build_narration`에 `relation` 포함(음성에도).
- **scripts**: `backfill-graph.sh`(사람 실행 — 운영 DB 쓰기).

## API/타입 변경 (계약 `api-contract-quality.py`)

- 신규 엔드포인트 없음(내부 파이프라인 개선). agent `Evidence`·`RelationEvidence`·`build_script(relations)` 타입 확장. research `/search` 응답 형태 불변(사실 dedup은 서버 내부).

## 검증 (실 컨테이너 스택 — localhost:8091)

- 백필: 309기사 → 404 종목·섹터 연관(그래프 엣지는 MERGE 유니크화).
- A1: 삼성전자 시나리오 `[relation] 삼성전자와 SK하이닉스 경쟁 구도` + `SK하이닉스는 반도체 관련주`(조사 정확). 현대차 `[relation] 현대차는 자동차 관련주`.
- A2: fact 3개 서로 다른 헤드라인(중복 0).
- 회귀: job#28 승인→ready(content 19). 단위테스트 news-feed 6·agent 3 통과.

## 특이사항 (설계 대비·후속)

- **이탈**: (1) 그래프 엣지 MERGE 유니크화로 카운트는 낮지만 종목별 커버리지 확보(근거=article). (2) 백필은 결정론적 섹터 엣지만 — 과거 기사 LLM 재추출은 Ollama 부하로 후속. (3) 사실 랭킹은 최신순+dedup, issue-detector 점수 연계는 후속.
- **다음**: Phase B(LLM 연결자·거시 문장화·citation guard) → Phase C(구간 장면·자막 싱크·신뢰 배지·TTS).
- 관계 문장은 현재 단문("~ 관련주"). Phase B에서 LLM이 사실·관계를 엮어 매끄럽게.
- 커밋: 아직(사람 게이트 — `/commit`). 백필은 운영 작업이라 스크립트로 사람이 실행.