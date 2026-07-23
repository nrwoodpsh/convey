# 20260723 — 요약: 엔티티 인식 확대 (개방형 NER + 수집 멱등 + 백필)

- **Task**: `doc/design/research/20260723-task-ner.md` (라운드㉚)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료·검증. 그래프가 46 사전을 넘어 개방형으로 채워짐. 수집 멱등으로 재추출 낭비 차단.

## 개요

그래프가 46 사전에 갇혀 노드 33·관계 69였다(기사 1,085 대비 빈약). 로컬 Ollama **개방형 추출**(엔티티+관계 1콜)로 사전 밖 기업·인물·사건을 그래프에 넣는다. 가드레일: 본문 substring 검증(환각컷)·근거 결속·엣지 제한. news-feed 폴링 재발행으로 인한 중복 재추출은 **수집 멱등**으로 차단. ADR 0014.

## 변경사항 (research)

- **extract/relations.py**: `extract_graph(text, seed, llm) -> Graph{entities, relations}` — Ollama 1콜 `{entities, relations}` 파싱, 엔티티 **본문 substring 검증**·정규화(`_normalize_entity`)·스톱워드(`ENTITY_STOPWORDS`)·min-len 필터, 관계는 (검증 엔티티∪seed)·엣지 어휘 제한. `extract_relations`(기존) 유지.
- **consumer.py `handle_ingested`**: **멱등** — `article_exists(source_url)`면 skip(재저장·재NER 안 함). 신규만 Article 저장 → `extract_graph` → `upsert_entity`(엔티티 노드) + `upsert_relation`(관계). 결정론 종목→섹터/사건 엣지 유지.
- **graph/neo4j_repo.py**: `_STOCK_BY_NAME`을 공유 마스터(common.stocks 46) 기반으로 · `upsert_entity`(단독 엔티티 노드) 추가.
- **domains/research/repository.py**: `article_exists(source_url)`.
- **backfill.py**: `--llm`이 `extract_graph` 사용(전량·재개).

## API/타입 변경

- 없음(내부 추출·그래프·수집 로직). 계약 `api-contract-ner.py`. 벡터 임베딩은 제외 유지(ADR 0006).

## 검증 (실 컨테이너 스택)

- 단위테스트: research 6 통과(extract_graph 환각컷·엣지 필터·스톱워드·seed 합집 포함).
- 멱등(AC3): 기사 수 **1145 안정**(news-feed 재발행에도 안 늘어남 → 중복 재추출 차단).
- 개방 추출(AC2): 사전 밖 인물 **"젠슨황"** 등 노드, 그래프 노드 33→36+ 증가.
- 백필(AC4): 소량 `--llm` 동작(extract_graph). 전량 1,085는 사람 실행(Ollama 부하).

## 특이사항 (설계 대비·후속)

- **이탈**: 완전 개체연결(동의어 병합)은 후속 — 정규화는 최소(공백·괄호·스톱워드). 라이브 NER는 신규 기사만(멱등)이라 부하 제한.
- **후속**: 전량 백필 사람 실행(`scripts/backfill-graph.sh` 확장/`app.backfill --llm`), entity linking 고도화, 엔티티 타입 라벨(:Person·:Event).
- 커밋: 아직(사람 게이트 — `/commit`). 소량 백필이 백그라운드로 진행 중(멱등·무해).