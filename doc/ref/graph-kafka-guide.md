# 그래프DB(Neo4j)·Kafka 학습 가이드 — 처음 배우는 사람을 위해

> **이 문서는 누구를 위한 것인가.** Kafka와 그래프DB를 처음 만지는 사람이, CONVEY 코드를 보며 "이게 왜 여기 있고, 무슨 뜻인지"까지 이해하도록 쓴 가이드다.
> 그래서 **개념 → 의미 → CONVEY에서의 쓰임 → 직접 해보기** 순서로 반복한다. 접속 정보와 명령어는 그대로 실행 가능하다.
> 로컬 도커 스택 기준. 기동 `scripts/up.sh` · 정지 `scripts/down.sh`. 운영 DB 직접 쓰기는 사람이 한다(가드레일).

---

## 0. 30초 요약 — 두 기술이 CONVEY에 왜 있나

CONVEY는 **주식 리서치를 유튜브 쇼츠로 바꾸는 자동 파이프라인**이다. 그 안에서 두 기술이 서로 다른 일을 한다.

| 기술 | 한 문장 정의 | CONVEY에서 맡는 일 | 이게 없으면 |
|:--|:--|:--|:--|
| **Neo4j (그래프DB)** | 데이터를 **점(노드)과 선(관계)**으로 저장하는 DB | "삼성전자 —[경쟁]→ SK하이닉스", "엔비디아 —[공급]→ 삼성전자" 같은 **종목·사건의 연결**을 저장 | 영상이 "오늘 올랐다"만 말하고 **왜 올랐는지(인과)**를 못 짚는다 |
| **Kafka (이벤트 버스)** | 서비스끼리 **메시지를 주고받는 중앙 우편함** | 기사 수집 → 그래프 저장 → 이슈 선별 → 스크립트 → 영상 합성을 **한 줄로 잇는다** | 서비스들이 서로 직접 전화를 걸어야 해서, 하나 죽으면 줄줄이 멈춘다 |

**핵심 연결고리**: CONVEY의 알파(차별점) 1번은 "근거 있는 정확한 정보"다. 그래프DB는 그 근거의 **뼈대(무엇이 무엇과 어떻게 엮였나)**를 담고, Kafka는 그 정보가 **수집부터 영상까지 새지 않고 흐르는 길**을 만든다.

```
[뉴스·시세]  --Kafka-->  [research: 그래프에 관계 저장(Neo4j)]  --Kafka-->  [이슈 선별]
     --Kafka-->  [스크립트 생성(그래프에서 인과 회수)]  --Kafka-->  [영상 합성]  --Kafka-->  [완성본]
```

---

# 1부. 그래프DB (Neo4j)

## 1-1. 왜 "그래프"인가 — 표와 무엇이 다른가

우리가 아는 보통의 DB(관계형·Postgres)는 **표(table)**다. 엑셀 시트처럼 행과 열이 있다. 표는 "삼성전자의 오늘 종가는 71,900원" 같은 **사실 하나**를 담기에 좋다.

문제는 **연결을 물을 때** 생긴다. "삼성전자와 경쟁하는 회사의, 그 회사에 부품을 대는 회사는?" 같은 질문은 표에서 JOIN을 여러 번 겹쳐야 하고, 깊어질수록 느리고 복잡해진다.

그래프DB는 반대다. **연결 자체를 데이터로** 저장한다.

| | 관계형 DB (표) | 그래프 DB (점·선) |
|:--|:--|:--|
| 저장 단위 | 행(row) | **노드**(점)와 **관계**(선) |
| "연결"을 표현 | 외래키 + JOIN(계산할 때마다 조립) | **관계가 그 자체로 저장**됨(이미 이어져 있음) |
| 잘하는 질문 | "이 종목의 값은?" | **"이 종목과 N단계로 엮인 것들은?"** |
| CONVEY 쓰임 | Postgres: 시세·기사 원문(사실) | Neo4j: 종목·사건의 **관계망(인과)** |

> **CONVEY에서의 의미**: 알파 1번 "정확한 근거"는 단순 수치가 아니라 **맥락**이다. "엔비디아 실적 발표 → HBM 수요 → 삼성전자·SK하이닉스 수혜" 같은 **연쇄**를 영상이 설명하려면, 그 연쇄가 어딘가에 **미리 이어진 형태로** 있어야 한다. 그게 그래프다. 이 방식을 **GraphRAG**(그래프에서 관련 사실을 꺼내 LLM 답변의 근거로 쓰는 것)라고 부른다.

## 1-2. 그래프의 4가지 기본 재료

그래프DB를 이해하려면 딱 4개만 알면 된다. CONVEY 실제 데이터로 설명한다.

```
        (노드)                    관계                      (노드)
   ┌───────────────┐      HAS_EVENT (선)          ┌──────────────┐
   │   삼성전자      │ ───────────────────────────▶│   실적발표     │
   │  :Entity       │      { source_article_id:    │  :Entity      │
   │  :Stock        │        1152 }  ← 속성         └──────────────┘
   │  name:'삼성전자'│
   │  ticker:'005930'│ ◀── 라벨 + 속성
   └───────────────┘
```

1. **노드(Node) = 점 = "무엇"**
   하나의 대상. CONVEY에선 종목·기업·인물·사건·섹터가 각각 노드다. 예: `삼성전자`, `젠슨황`, `실적발표`, `반도체`.

2. **관계(Relationship) = 선 = "어떻게 엮였나"**
   두 노드를 잇는 **방향 있는 화살표**. CONVEY는 **5종류만** 허용한다(아무 관계나 못 만든다 — 뒤에서 설명):

   | 관계 | 뜻 | 예 |
   |:--|:--|:--|
   | `HAS_EVENT` | ~에 사건이 있었다 | 삼성전자 → 실적발표 |
   | `AFFECTS` | ~에 영향을 준다 | 금리인상 → 반도체 |
   | `SUPPLIES` | ~에 공급한다 | 삼성전자 → 애플 |
   | `COMPETES` | ~와 경쟁한다 | 삼성전자 → SK하이닉스 |
   | `BELONGS_TO` | ~에 속한다(섹터) | 삼성전자 → 반도체 |

3. **속성(Property) = 점·선에 붙는 상세**
   노드/관계에 딸린 키-값. 예: 노드 `삼성전자`의 `ticker: '005930'`. 관계의 `source_article_id: 1152`.

4. **라벨(Label) = 노드의 종류 태그**
   노드가 어떤 부류인지 나타내는 꼬리표. CONVEY 규칙:
   - **모든 노드는 `:Entity`** 라벨을 단다(공통 부류).
   - 그중 **아는 종목이면 `:Stock` 라벨을 추가로** 달고 `ticker` 속성을 붙인다(멀티 라벨). 코드: `neo4j_repo.py`의 `_label_stock()`.

> **CONVEY에서의 의미 — 관계의 `source_article_id`가 왜 결정적인가**: 모든 관계에는 그 관계를 **뒷받침한 기사 id**가 반드시 붙는다(`upsert_relation`이 `SET r.source_article_id` 강제). 이게 알파 1번의 뼈대다 — "삼성전자가 SK하이닉스와 경쟁한다"는 선이 **어느 기사에서 나왔는지** 추적되므로, **무출처 주장(환각)을 만들 수 없다.** 근거 없는 선은 애초에 저장되지 않는다.

## 1-3. Cypher 읽는 법 — 그림을 글자로 그린다

Neo4j의 질의 언어는 **Cypher**다. SQL이 표를 위한 언어라면, Cypher는 **그림(점·선)을 아스키로 그리는** 언어다. 핵심 문법 하나만 익히면 된다:

```
(노드)-[관계]->(노드)
 괄호=점   대괄호=선   화살표=방향
```

읽는 법 — 실제 쿼리를 한국어로 옮겨보자:

```cypher
MATCH (s:Entity {name:'삼성전자'})-[r]->(o)  RETURN s.name, type(r), o.name;
```
→ "이름이 **삼성전자**인 `:Entity` 노드에서, **밖으로 나가는 모든 선 `r`**을 타고 도착한 노드 `o`를 찾아라. 그 시작 이름·관계 종류·도착 이름을 보여줘."

- `MATCH` = 찾아라(SQL의 SELECT ... FROM ... WHERE에 해당하는 '패턴 매칭').
- `(s:Entity {name:'…'})` = `:Entity` 라벨에 그 이름을 가진 노드, 별명 `s`.
- `-[r]->` = `s`에서 **나가는** 관계, 별명 `r`. 화살표 방향이 곧 관계 방향.
- `RETURN` = 결과로 무엇을 보여줄지.

> **의미**: Cypher를 읽을 줄 알면 그래프에 "무엇이 무엇과 엮였나"를 직접 물어볼 수 있다. CONVEY의 스크립트 생성기(`agent`)가 하는 일이 바로 이것 — 종목 이름을 넣고 관계를 꺼내 영상 대본의 "인과 문장"으로 만든다.

## 1-4. 접속 정보

| 항목 | 값 | 의미 |
|:--|:--|:--|
| 브라우저(웹 UI) | **http://localhost:7474** | 사람이 쿼리 치고 **그래프를 그림으로 보는** 곳 |
| Bolt(드라이버·CLI) | `bolt://localhost:7687` | 코드·`cypher-shell`이 **프로그램으로 접속**하는 포트 |
| 사용자 / 비밀번호 | `neo4j` / `convey-dev-pw` | `.env`의 `NEO4J_AUTH=neo4j/…` |

> 포트가 왜 2개인가: **7474는 사람용(웹 화면)**, **7687은 기계용(드라이버 프로토콜 Bolt)**이다. 우리 파이썬 코드(`GraphDatabase.driver`)는 7687로 붙는다.

## 1-5. 웹 UI로 눈으로 보기 (처음이라면 여기부터)

1. 브라우저 `http://localhost:7474` 접속.
2. Connect URL `bolt://localhost:7687`, ID `neo4j`, PW `convey-dev-pw` 입력.
3. 상단 입력창에 아래 쿼리를 넣고 ▶ 실행. **점과 선이 그림으로** 뜬다.

```cypher
// 그래프 전체 맛보기 — 관계 100개를 그림으로 (여기서부터 시작하면 감이 온다)
MATCH p=()-[r]->() RETURN p LIMIT 100;
```
→ 화면에 동그라미(노드)와 화살표(관계)가 뜬다. 동그라미를 끌어보고, 클릭해 속성을 확인해보라. **이 그림이 곧 CONVEY가 세상을 이해하는 방식**이다.

## 1-6. 손으로 해보는 Cypher — 쿼리마다 "무엇을 묻고, 왜 CONVEY에 중요한가"

CLI로도 같은 쿼리를 실행할 수 있다(컨테이너 안):

```bash
docker compose exec neo4j cypher-shell -u neo4j -p convey-dev-pw \
  "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;"
```

아래는 자주 쓰는 쿼리 모음이다. **각 쿼리가 무엇을 묻고, CONVEY에서 어떤 의미인지** 함께 적었다.

```cypher
// ① 관계 유형별 개수 — "그래프가 얼마나 풍부한가"의 건강검진
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;
```
> **의미**: BELONGS_TO(섹터)만 많고 COMPETES·AFFECTS(LLM이 뽑은 인과)가 적으면, 영상이 "무슨 섹터다" 수준에 그친다. 이 숫자가 곧 **영상이 설명할 수 있는 인과의 깊이**다.

```cypher
// ② 특정 종목의 이웃 — "삼성전자는 무엇과 엮여 있나"
MATCH (s:Entity {name:'삼성전자'})-[r]->(o) RETURN s.name, type(r), o.name;
```
> **의미**: 스크립트 생성기가 삼성전자 영상을 만들 때 **꺼내오는 바로 그 정보**. 이웃이 많고 다양할수록 대본이 풍부해진다.

```cypher
// ③ 종목 → 사건 — "오늘 이 종목에 무슨 일이 있었나"
MATCH (s)-[:HAS_EVENT]->(e) RETURN s.name, e.name LIMIT 25;
```
> **의미**: 알파 2번 "이슈 종목 자동 선별"의 원재료. 사건이 걸린 종목이 곧 오늘의 이슈 후보다.

```cypher
// ④ 경쟁·공급 구도 — "이 산업의 지도"
MATCH (a)-[r:COMPETES|SUPPLIES]->(b) RETURN a.name, type(r), b.name;
```
> **의미**: 영상에서 "경쟁사 대비", "공급망 수혜" 같은 **맥락 문장**을 만들 근거.

```cypher
// ⑤ 다홉 추론 — "삼성전자에서 2단계 안에 닿는 모든 것"
MATCH p=(s:Entity {name:'삼성전자'})-[*1..2]->(o) RETURN p LIMIT 50;
```
> **의미**: `[*1..2]`는 "선을 1~2번 타고 가라"는 뜻. 그래프의 진짜 힘이 여기 있다 — **직접 안 엮인 것도 연쇄로 닿는다.** CONVEY 코드 `relations_of(hops=…)`가 이걸 한다(최대 3홉).

```cypher
// ⑥ 근거 확인 — "이 관계, 어느 기사에서 나왔나" (환각 감사)
MATCH ()-[r]->() RETURN type(r), r.source_article_id LIMIT 10;
```
> **의미**: 가드레일 점검. `source_article_id`가 비어 있으면 안 된다 — **무출처 관계는 존재하면 안 되기 때문**(알파 1). 이 쿼리로 무출처 오염을 잡는다.

```cypher
// ⑦ 종목 노드만 — :Stock 라벨이 붙은 것(ticker 보유)
MATCH (n:Stock) RETURN n.name, n.ticker ORDER BY n.name;
```
> **의미**: `:Entity` 중 우리가 **아는 종목**만. 이들만 시세(Postgres PriceTick)와 ticker로 연결된다.

> 노드 라벨: `:Entity`(모든 엔티티 공통) / `:Stock`(아는 종목 — `ticker` 속성). 관계는 5종(`HAS_EVENT`·`AFFECTS`·`SUPPLIES`·`COMPETES`·`BELONGS_TO`)뿐이고, 모두 `source_article_id`로 근거에 묶인다.

## 1-7. 이 그래프는 어떻게 채워지나 (CONVEY 내부)

학생이 가장 궁금해할 것 — "이 점과 선을 누가 넣나?"

```
기사 본문  ──▶  research 서비스의 개방형 NER(로컬 Ollama LLM 1콜)
                 │   "본문에서 엔티티와 관계를 JSON으로 뽑아줘"
                 ▼
            환각 컷: 뽑힌 엔티티가 본문에 실제로 있는 글자인지 검사(substring)
                 │   (없으면 버림 — 알파 1)
                 ▼
            upsert_entity(점) + upsert_relation(선, source_article_id 결속)
                 │   허용된 5개 엣지만, 근거 기사 id 필수
                 ▼
              Neo4j 그래프에 누적
```

- 코드: `services/research/app/extract/relations.py`(추출) → `consumer.py`(적용) → `neo4j_repo.py`(저장).
- **멱등**: 같은 기사(source_url)는 다시 처리하지 않는다 → 그래프에 중복 폭증 없음.
- **백필**: 과거 기사 전체를 소급 처리해 그래프를 채우는 배치 → `python -m app.backfill --llm`.

> **왜 규칙(5개 엣지·substring 검증)이 이렇게 엄격한가**: LLM은 그럴듯한 거짓(환각)을 잘 만든다. 아무 관계나 저장하면 그래프가 오염되고, 그 오염이 영상의 "근거"로 나간다. 그래서 **좁고 검증된 것만** 들인다. 이 엄격함이 알파 1번을 지키는 값이다.

---

# 2부. Kafka (이벤트 버스)

## 2-1. 왜 "이벤트 버스"인가 — 직접 전화 vs 우편함

CONVEY는 여러 작은 서비스(MSA)로 쪼개져 있다: `news-feed`, `research`, `issue-detector`, `content`, `video-assembly`… 이들이 **어떻게 협력하느냐**가 문제다.

**나쁜 방법 — 직접 호출(직접 전화)**: news-feed가 research에게 직접 API를 건다. research가 issue-detector에게 또 건다. 이러면:
- research가 잠깐 죽으면 news-feed도 막힌다(**연쇄 장애**).
- 새 서비스를 끼우려면 누가 누구를 부르는지 배선을 다 고쳐야 한다(**강결합**).
- 갑자기 기사가 몰리면 처리 못 한 요청이 그냥 사라진다(**유실**).

**좋은 방법 — 이벤트 버스(중앙 우편함)**: news-feed는 "기사 왔음"이라는 **메시지를 우편함(토픽)에 넣기만** 한다. 누가 가져가는지 신경 안 쓴다. research는 그 우편함을 **구독**해 자기 속도로 꺼내 처리한다.

| | 직접 호출 | Kafka 이벤트 버스 |
|:--|:--|:--|
| 결합도 | 강함(서로를 안다) | **느슨함**(우편함만 안다) |
| 하나 죽으면 | 연쇄로 멈춤 | 메시지가 **쌓여 기다림**, 살아나면 이어 처리 |
| 트래픽 폭증 | 유실·과부하 | **버퍼**로 흡수(밀리면 lag) |
| 새 소비자 추가 | 배선 수정 | 그냥 **구독만** 추가 |

> **CONVEY에서의 의미**: 파이프라인이 "수집 → 그래프 → 선별 → 스크립트 → 합성 → 완성"으로 길다. 각 단계 속도가 다르다(영상 합성은 ffmpeg라 느리다). Kafka가 사이에 있어 **느린 단계가 빠른 단계를 막지 않고**, 한 서비스를 재시작해도 **일이 유실되지 않는다.** 이게 자동 양산(알파 4)의 토대다.

## 2-2. Kafka 기본 용어 6개

```
프로듀서(넣는 쪽)              토픽 "research.ingested"              컨슈머(꺼내는 쪽)
 news-feed  ──메시지──▶  [ 0 | 1 | 2 | 3 | 4 | 5 ... ]  ──▶  research
                          ↑                    ↑
                        오프셋(줄 번호)      여기까지 읽음(커서)
```

| 용어 | 뜻 | 비유 |
|:--|:--|:--|
| **토픽(Topic)** | 메시지가 쌓이는 이름 붙은 통로 | 우편함(주소) |
| **프로듀서(Producer)** | 메시지를 넣는 서비스 | 편지 보내는 사람 |
| **컨슈머(Consumer)** | 메시지를 꺼내 처리하는 서비스 | 편지 받는 사람 |
| **오프셋(Offset)** | 토픽 안 메시지의 순번(줄 번호) | 몇 번째 편지인지 |
| **컨슈머 그룹(Consumer Group)** | 같은 일을 나눠 하는 컨슈머 묶음 | 우편함 하나를 나눠 처리하는 팀 |
| **랙(Lag)** | 쌓인 양 − 처리한 양 = **밀린 개수** | 안 읽은 편지 수 |

> **오프셋의 의미**: Kafka는 메시지를 꺼내도 **지우지 않는다.** 컨슈머가 "나 여기까지 읽음"이라는 **커서(오프셋)**만 옮긴다. 그래서 컨슈머가 죽었다 살아나도 **읽던 자리부터** 이어갈 수 있고, 필요하면 커서를 되감아 **과거 메시지를 재생**할 수도 있다(`--from-beginning`).

> **랙(lag)의 의미 — 가장 중요한 건강 지표**: 랙이 0에 가까우면 컨슈머가 실시간으로 따라잡고 있다는 뜻. 랙이 계속 커지면 **그 서비스가 병목**이라는 신호다. CONVEY에서 `media.assemble`의 랙이 쌓이면 → "영상 합성이 밀린다 = ffmpeg가 못 따라간다"로 바로 읽힌다.

## 2-3. 접속 정보

| 항목 | 값 | 의미 |
|:--|:--|:--|
| **kafka-ui(웹 UI)** | **http://localhost:8090** | 토픽·메시지·랙을 **눈으로 보는** 대시보드 |
| 호스트 부트스트랩(외부) | `localhost:29092` | 내 PC의 툴·스크립트가 붙는 주소 |
| 컨테이너 내부 | `kafka:9092` | 도커 안 서비스끼리 쓰는 주소 |

> 주소가 2개인 이유: 도커 **안**의 서비스는 `kafka:9092`로, 도커 **밖**(내 PC)의 툴은 `localhost:29092`로 붙는다. 같은 카프카를 보는 두 개의 문이다.

## 2-4. CONVEY 토픽 지도 = 곧 파이프라인 그림

토픽 목록을 읽으면 **CONVEY가 어떻게 동작하는지가 그대로 보인다.** 토픽 = 파이프라인의 단계별 관문이다.

```
market-feed ─▶ market.ticks ──────────┐
news-feed   ─▶ research.ingested ──────┼─▶ research (그래프 저장·NER)
news-feed   ─▶ research.macro ─────────┘
                                        │
                        research ─▶ issue.selected ─▶ issue-detector가 고른 이슈
                                        │
                              content ─▶ content.generate (자기 작업 큐)
                                        │
                              content ─▶ media.assemble ─▶ video-assembly (ffmpeg 합성)
                                        │
                    video-assembly ─▶ content.assembled ─▶ content (합쳐진 결과 수신)
                                        │
                              content ─▶ content.ready (완성) ─▶ content.approved (사람 승인 후 발행)
```

| 토픽 | 흐름(누가→누가) | 의미 |
|:--|:--|:--|
| `market.ticks` | market-feed → research | 시세 스트림(KIS OpenAPI) |
| `research.ingested` | news-feed → research | 기사·공시 도착 → **그래프 저장·NER의 입구** |
| `research.macro` | news-feed → research | 거시지표(금리·환율 등) |
| `issue.selected` | issue-detector → content | **오늘의 이슈 종목**(알파 2) → 자동 양산 방아쇠 |
| `content.generate` | content → 자기 consumer | 생성 작업 큐(스크립트부터 시작) |
| `media.assemble` | content → video-assembly | "이 자산으로 영상 합쳐줘" |
| `content.assembled` | video-assembly → content | 합성 완료 신호(fan-in — 여러 조각이 하나로 모임) |
| `content.ready` / `content.approved` | content 내부 / 발행 | 완성본 / **사람 승인 후에만** 발행(가드레일) |

> **의미**: `issue.selected`가 발행되는 순간이 **완전 자동 양산의 시작점**이다. 사람이 안 눌러도 이슈가 잡히면 스크립트→영상까지 굴러간다. 반대로 **맨 끝 `content.approved`는 사람이 승인해야만** 넘어간다 — 자동은 완성본 생성까지, 유튜브 업로드는 사람 손(가드레일).

## 2-5. 손으로 관찰하기 — 각 명령이 무엇을 보여주나

### 웹 UI (처음이라면 여기부터)
1. `http://localhost:8090` 접속(로그인 없음).
2. 좌측 **Topics** → 토픽 클릭 → **Messages** 탭 → 실제 오간 메시지(JSON)를 본다.
3. **Consumers** 탭 → 각 컨슈머 그룹의 **lag**을 본다 → 밀리는 서비스가 한눈에.

> **의미**: Messages 탭은 "파이프라인에 실제로 무슨 데이터가 흐르나"를 보여주고, Consumers 탭의 lag은 "어디가 막혔나"를 보여준다. 디버깅의 출발점이다.

### CLI (컨테이너 안)
```bash
# 토픽 목록 — "파이프라인에 어떤 관문이 있나"
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```
> 위 지도의 토픽들이 실제 존재하는지 확인.

```bash
# 특정 토픽의 최근 메시지 3건 엿보기 — "여기 무슨 데이터가 흐르나"
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic research.ingested --from-beginning --max-messages 3
```
> `--from-beginning`은 **커서를 맨 앞으로 되감아** 과거부터 본다(오프셋 개념의 실습). `--max-messages 3`으로 3건만 보고 멈춘다.

```bash
# 실시간 관찰 — 새 메시지가 들어오는 걸 라이브로 (멈추려면 Ctrl+C)
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic research.ingested
```
> 새 기사가 수집되는 순간 여기 뜬다. 파이프라인이 **살아 움직이는 걸** 눈으로 확인.

```bash
# 컨슈머 그룹의 랙 확인 — "어느 단계가 밀리나" (병목 진단)
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 --describe --all-groups
```
> `LAG` 열이 계속 커지는 그룹 = 병목. 예: video-assembly 그룹의 lag이 크면 영상 합성이 못 따라가는 것.

---

# 3부. (참고) Postgres — 그래프와 역할 분담

Neo4j가 **관계(뼈대)**를 맡는다면, Postgres는 **사실(살)**을 맡는다. 둘은 경쟁이 아니라 분업이다.

| | Neo4j | Postgres |
|:--|:--|:--|
| 담는 것 | 종목·사건의 **연결(인과)** | 기사 원문·시세 **수치(사실)** |
| 질문 | "무엇과 엮였나" | "정확한 값은 얼마인가" |
| 알파 연결 | 근거의 **맥락** | 근거의 **수치**(차트·수치 렌더 알파 3) |

| 항목 | 값 |
|:--|:--|
| 접속 | `localhost:5432` · user `app` · pass `app` |
| DB | `research_db`(articles·price_ticks·macro_indicators) · `content_db`(generation_jobs·scripts·contents) |

```bash
# 완성 쇼츠 목록 — 어떤 영상이 만들어졌나
docker compose exec postgres psql -U app -d content_db \
  -c "select j.id,j.status,j.topic,c.mp4_path from generation_jobs j left join contents c on c.job_id=j.id order by j.id desc limit 10;"

# 오늘자 기사 — 그래프의 원재료
docker compose exec postgres psql -U app -d research_db \
  -c "select id,title,tickers,published_at from articles order by published_at desc limit 10;"
```
> GUI(DBeaver·TablePlus)로 붙을 땐 **Database에 `research_db` 또는 `content_db`를 지정**해야 테이블이 보인다(기본 `app`/`postgres` DB는 비어 있음).

> **의미 — 왜 굳이 DB를 둘로 나누나**: 영상 대본을 만들 때 그래프에서 "삼성전자 —[경쟁]→ SK하이닉스"라는 **관계**를 꺼내고, Postgres에서 "종가 71,900원 +2.34%"라는 **수치**를 꺼내 합친다. 관계(그래프)는 유연해야 하고 수치(표)는 정확·집계에 강해야 해서, **각자 잘하는 DB에 맡긴다.**

---

# 4부. 데이터 초기화 (실습·테스트 정리)

```bash
scripts/reset-data.sh          # 잡·영상만 지움(기사·그래프는 유지)
scripts/reset-data.sh --all    # 기사·시세·그래프까지 전부(피드가 다시 수집)
docker compose down -v         # 볼륨까지 완전 초기화(스키마는 Alembic이 재생성)
```
> **의미**: `--all`은 그래프까지 비운다. 처음부터 다시 쌓이는 과정을 관찰하고 싶을 때 유용하지만, LLM NER 백필을 다시 돌려야 그래프가 채워진다(수 시간). 가볍게 잡·영상만 정리하려면 인자 없이.

---

# 5부. 한 장 치트시트

```
● 웹으로 보기
  Neo4j 그래프    http://localhost:7474   (neo4j / convey-dev-pw)
  Kafka 대시보드   http://localhost:8090   (로그인 없음)

● Neo4j — 무엇이 무엇과 엮였나 (관계 = 근거의 뼈대, 알파 1)
  MATCH p=()-[r]->() RETURN p LIMIT 100;                      // 전체 그림
  MATCH (s:Entity{name:'삼성전자'})-[r]->(o) RETURN s.name,type(r),o.name;  // 이웃
  MATCH ()-[r]->() RETURN type(r),count(*) ORDER BY count(*) DESC;         // 건강검진

● Kafka — 파이프라인이 흐르는 길 (토픽 = 단계별 관문)
  ...--list                              // 관문 목록
  ...--topic research.ingested           // 이 관문에 흐르는 데이터
  ...consumer-groups --describe          // 어디가 밀리나(LAG)

● 핵심 개념 3줄
  그래프 = 점(노드)+선(관계), 선마다 근거 기사 id → 무출처 없음(환각 방지)
  Kafka  = 서비스 사이 우편함, 메시지 안 지움(오프셋 커서), 밀리면 lag
  분업   = Neo4j 관계 / Postgres 수치 → 대본은 둘을 합쳐 만든다
```

---
> 이 문서는 학습용 참조(`doc/ref/`)다. 접속값·토픽은 코드(`compose`·`config.py`·`neo4j_repo.py`)가 정본이며, 바뀌면 여기도 갱신한다.
