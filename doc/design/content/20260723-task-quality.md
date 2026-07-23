# 20260723-task-quality.md

> 라운드 ㉕ (품질 향상 — 알파 복원: 그래프 인과·LLM 편집자·연출). ADR 0012.
> 통합 설계 1개, 구현은 **Phase A→B→C 단계별**(각 판 실 스택 검증). 계약: `api-contract-quality.py`.

## 1. Requirements

- **문제(결론)**: 영상이 "헤드라인 원문 + 종가/등락 + 거시 숫자 덤프"의 나열이라 지루하고 제품화 어려움. **핵심 원인 — 알파("그날 기사 × 그래프 인과")가 코드에서 끊겨 있음**: agent `Evidence`에 `relations` 필드가 없어 research `/search`가 준 그래프 관계를 버린다 → `build_script`에 인과가 0.
- **목표**: (A) 그래프 인과를 스크립트까지 실제로 흘려 "왜/맥락"을 만들고, 사실을 큐레이션(중복 제거·중요도)한다. (B) LLM을 창작자가 아닌 **연결자**로 써 문장을 매끄럽게(수치·관계는 사실 결속, 환각 0). (C) 장면 전환·자막 싱크·신뢰 배지·TTS로 연출.
- **단계**: **Phase A(데이터) → B(문장) → C(연출)**. A만으로도 헤드라인 리더에서 탈출.
- **Acceptance Criteria** (측정 가능):
  - **Phase A** ✅ (구현·실 스택 검증)
    - [x] A1: agent `Evidence.relations` 부활 → `build_script` **`relation` 섹션**. **검증: "삼성전자와 SK하이닉스 경쟁 구도"·"SK하이닉스는 반도체 관련주"**(조사 자동). +내레이션에 relation 포함.
    - [x] A2: 사실 **중복 제거**(정규화 제목 dedup, 최신순 유지) → **검증: fact 3개 서로 다른 헤드라인**(이전 동일 반복 사라짐).
    - [x] A3: 엔티티 사전 6→20 + 섹터 + **단일 종목→섹터 엣지**(결정론) + **백필 309기사→섹터 엣지**. **검증: (현대차)-BELONGS_TO->(자동차) 등, 주요 종목 관계 커버.**
  - **Phase B** ✅ (구현·실 스택 검증)
    - [x] B1: 훅이 **실제 뉴스에 근거**(LLM+citation guard) + 헤드라인 정리([태그]·말줄임 제거). **검증: "현대차 노사 대립 종식 필요, 생산차질 지속"·"현대차 노사, 대립의 시간 끝내야"**(이전 필러·[태그] 사라짐). 환각 수치 차단.
    - [x] B2: 거시 숫자 덤프 → **문장**(2개 한정). **검증: "거시 환경도 함께 보면, … 수준입니다."**
  - **Phase C**
    - [ ] C1: `media.assemble`에 `segments`(구간 자막+음성) → **구간별 자막 싱크**·수치 구간 팝. 정적 1화면 탈피.
    - [ ] C2: **신뢰 배지**(출처·날짜) 화면 표시(무출처면 미표시).
    - [ ] C3: TTS가 구간 단위로 끊어 읽어(쉼) 밋밋함 완화.
  - [ ] 공통: 실 컨테이너 스택 재생성으로 각 Phase 육안 검증(mp4·시나리오).

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **관계 근거 결속**: relation 섹션도 `source_article_id`(→source_url) 결속 필수(무출처 관계 폐기). 그래프 관계엔 수치 없음 — 수치는 여전히 price/macro 슬롯만.
  - **그래프 희소**(전 논의): 확대·백필 안 하면 A1이 만들 관계가 거의 없음 → **A3가 A1의 전제**. 백필은 일회성 관리작업(운영 DB 쓰기 → 사람 실행, 가드레일).
  - **LLM 편집자 리스크(B)**: 연결 문장에 LLM이 수치·미검증 주장을 끼워 넣을 위험 → 수치는 슬롯만, 문장은 "주어진 사실만 잇기" 프롬프트 + **인용 검증(citation guard) 유지**. 어기면 폐기·재생성.
  - **연출(C) ffmpeg 비용**: 구간 전환은 concat/xfade로 렌더 시간↑. 세그먼트 수 제한(3~5). 실패 시 단일 자막(기존)로 안전 강등.
  - **TTS 세그먼트**: edge-tts SSML 지원 제한 — 구간별 파일 생성→concat(무음 삽입)으로 대체 가능.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 관계 투입 위치**: 택함 = **agent retriever `Evidence.relations` + build_script `relation` 섹션** / 기각 = research가 문장 생성(경계 위반·LLM 위치) / 사유 = 스크립트=agent 책임, research는 사실만.
  - **결정 2 — 그래프 확대 방식**: 택함 = **엔티티 사전 확대(공유 `common.stocks`+섹터·인물) + 단일 엔티티 자동 엣지(종목–사건/섹터)** + 백필 / 기각 = NER 모델 도입(무겁·후속) / 사유 = 최소 작업으로 커버리지↑.
  - **결정 3 — LLM 역할**: 택함 = **연결자**(주어진 사실·관계만 잇는 문장, 수치 슬롯 고정) / 기각 = 자유 서술(환각 위험·알파 위배) / 사유 = 정확성 알파 불가침. ADR 0012.
  - **결정 4 — 연출 데이터 경로**: 택함 = **`media.assemble`에 `segments`/`trust` 확장(하위호환 — 없으면 기존 단일 자막)** / 기각 = 별도 이벤트 / 사유 = 기존 fan-in 유지·점진 도입.
  - **결정 5 — 사실 큐레이션 위치**: 택함 = **research /search에서 중요도·dedup 부여**(사실 소유자) / 기각 = agent에서 필터 / 사유 = 데이터 품질은 research 책임(중복은 그쪽 조회에서).

## 3. UI/UX (영상 연출 — Phase C)

```
정적 1화면(현재)  →  구간(segment)별 장면 전환 + 자막 싱크
┌ 9:16 ─────────────┐   비트1(hook)   비트2(chart·수치 팝)  비트3(relation)  비트4(fact)
│ 제목 · 현대차(005380)│   배경A          수치 확대·강조         인과 그래프 톤     헤드라인 요약
│ [큰 차트/수치]      │   자막=음성구간1  자막=구간2            자막=구간3        자막=구간4
│ 하단 자막(구간 동기) │   ────────────── 신뢰 배지: 한국경제 · 2026-07-23 (우상단, 작게) ──────
└────────────────────┘
```
- 대시보드(시나리오 수정)엔 `relation` 섹션도 편집 대상으로 노출(출처는 계속 숨김 — ㉔).
- 배경 real/anim(㉔) 유지. 신뢰 배지는 "정확 데이터" 알파를 시청자가 체감하는 장치.

## 4. Logic (Phase별)

### Phase A — 데이터
- **retriever**(`agent/rag/retriever.py`): `Evidence`에 `relations: list[RelationEvidence]` 추가, `gather`가 `/search`의 `relations`(무출처 제외)를 파싱해 채움.
- **build_script**: `relations` 인자 추가 → `EDGE_KO` 매핑으로 `relation` 섹션 생성(관계당 1문장, 근거 결속). 템플릿(㉔)별 포함 개수 조정(속보=0~1, 분석=2~3, 스토리=1).
- **research /search**(P3): 사실에 `score`(최신성+issue 점수)·`dedup_key`(제목 정규화) 부여 → 중복 병합·정렬 후 상위 반환(`FactHitRanked`).
- **그래프 확대**(P2): 엔티티 사전 확대(코스피 주요+섹터+인물) — `common.stocks`/`news-feed TICKER_DICT` 통합·확장. `neo4j_repo`에 단일 엔티티 엣지(종목→섹터 `BELONGS_TO`, 종목→사건 `HAS_EVENT`) 자동 생성. **백필**: 기존 `articles` 재추출 스크립트(`scripts/backfill-graph.*`, 사람 실행).

### Phase B — 문장
- **build_script**: `fact`/`relation` 섹션 텍스트를 LLM 연결 문장으로("다음 사실들만 자연스럽게 이어라, 숫자·새 주장 금지"). 수치는 chart/macro 슬롯 유지. **citation guard**: 생성 문장이 근거 밖 수치/주장 포함 시 폐기→원문 fallback.
- **macro 문장화**: "거시 맥락 — {덤프}" → "{name} {value}{unit}(으)로 …" 짧은 문장(값 슬롯).

### Phase C — 연출
- **content**: `media.assemble` 발행 시 `segments`(섹션→구간 자막+음성)·`trust`(출처 호스트·날짜)·`background` 실어보냄(`media.build_assemble_event` 확장, 하위호환).
- **video-assembly**: `segments` 있으면 구간별 배경/차트 상태 + 자막 싱크(ffmpeg concat/xfade, 수치 구간 확대), 없으면 기존 단일. 신뢰 배지 drawtext(우상단). TTS는 구간별 합성→무음 concat.

## 5. Implementation Split (Phase = /run 3판)

- **Phase A**: `agent/rag/retriever.py`·`agent/script/builder.py`(relations·relation 섹션) · `research`(/search dedup·score) · `research/graph/neo4j_repo.py`+`news-feed/tagging.py`+`libs/common/stocks.py`(엔티티 확대·단일 엣지) · `scripts/backfill-graph.*`.
- **Phase B**: `agent/script/builder.py`(LLM 연결자·citation guard·macro 문장).
- **Phase C**: `content`(media.build_assemble_event 확장)·`video-assembly`(assemble.py·render.py 구간·배지·TTS concat)·대시보드 relation 편집 노출.

## 6. File Map (기계적)

- `[Mod] services/agent/app/rag/retriever.py` — Evidence.relations + gather 파싱
- `[Mod] services/agent/app/script/builder.py` — relations 인자·relation 섹션(A)·LLM 연결자·citation guard·macro 문장(B)
- `[Mod] services/research/app/domains/research/{service,repository,schemas}.py` — 사실 score·dedup(A)
- `[Mod] services/research/app/graph/neo4j_repo.py` · `services/news-feed/app/tagging.py` · `libs/common/common/stocks.py` — 엔티티 확대·단일 엣지(A)
- `[New] scripts/backfill-graph.sh` (+ 파이썬 잡) — 기존 기사 관계 재추출(A, 사람 실행)
- `[Mod] services/content/app/domains/content/media.py` — build_assemble_event segments·trust·background(C)
- `[Mod] services/video-assembly/app/{worker,assemble,render}.py` · `tts.py` — 구간 장면·자막 싱크·배지·TTS concat(C)
- `[Mod] services/content/app/static/index.html` — 시나리오 수정에 relation 섹션(C)
- `[New] doc/design/content/api-contract-quality.py` — 타입 계약

## 7. Verification (Phase별, 실 스택)

- **A**: 관계 있는 종목 생성 → 시나리오에 `relation` 문장(근거 결속) 노출·중복 헤드라인 0. 백필 후 Neo4j 관계 수↑(전/후 카운트). 
- **B**: 시나리오 문장이 매끄럽되 수치=사실(인용 검증 통과). 거시 문장화 확인.
- **C**: mp4에 구간 전환·자막 싱크·수치 팝·신뢰 배지 육안. segments 없을 때 기존 단일 자막 회귀.
- 각 Phase mypy·계약·ruff 통과. `/run` 실패 시 그 Phase에서 정지.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260723 | /builder(Phase B) | 문장 품질(agent builder). **B1**: 훅 프롬프트를 실제 뉴스(제목+리드 사실) 기반으로 재작성(이전 "주식 쇼츠 도입" 필러 제거) + `_clean_fact`(헤드라인 [태그]·글머리표·말줄임 정리, LLM 미개입·사실 불변) + **citation guard `_no_new_digits`**(생성 문장의 환각 수치 차단, 위반 시 폴백). **B2**: `_macro_sentence`(거시 5덤프→2개 문장, 값=슬롯). 템플릿 hook 필드를 톤 지시로 축소. **검증(실 스택)**: 현대차 job#29 훅 "현대차 노사 대립 종식 필요, 생산차질 지속", fact "현대차 노사, 대립의 시간 끝내야"(정리됨), 거시 문장화; 승인→ready 회귀0; agent 단위테스트 3 통과. **이탈**: 근사 중복 헤드라인(다른 어휘)은 exact-dedup이 못 잡음(후속), 거시 지표명 단위 노이즈(CPI 기준연도) 잔존(후속). |
| 20260723 | /builder(Phase A) | 알파 데이터 복원 구현·검증. **A1**: agent `Evidence.relations`+`gather` 파싱, `build_script(relations)`→`relation` 섹션(`EDGE_KO`→조사 자동 `_josa`), main.py가 relations 전달. **A1 gap 수정**: agent가 그래프 조회 entity를 티커코드→**종목명**으로(노드가 이름이라 매칭 안 되던 것). content `build_narration`에 `relation` 포함(음성에도). **A2**: research `/search` 사실 정규화 dedup(최신순). **A3**: `common.stocks` 20종목+섹터맵+`sector_of`, news-feed `tag_entity_names`가 종목+섹터 allow-list, research consumer 결정론적 종목→섹터 `BELONGS_TO` 엣지, `app/backfill.py`+`scripts/backfill-graph.sh`(과거 기사 백필). **검증(실 스택)**: 백필 309기사→404 연관; 삼성전자 시나리오에 경쟁·섹터 관계+조사 정확; fact 중복0; job#28→ready 회귀0; 단위테스트 news-feed 6·agent 3 통과. **이탈**: (1)그래프 엣지는 MERGE로 유니크화→카운트는 낮지만 종목별 커버리지 확보(근거=article), (2)백필은 결정론적 섹터엣지만(과거 LLM 재추출은 Ollama 부하로 후속), (3)사실 랭킹은 최신순+dedup(issue 점수 연계는 후속). |
| 20260723 | /design | 품질 향상 통합 설계 — 알파 복원. **결정적 진단: agent Evidence에 relations 없어 그래프 인과가 영상에 0.** Phase A(관계 투입·사실 큐레이션·그래프 확대+백필) → B(LLM 연결자·거시 문장, 환각0 유지) → C(구간 장면·자막 싱크·신뢰 배지·TTS). 계약 `api-contract-quality.py`(mypy 통과). ADR 0012 제안. 구현은 Phase별 /run. |
