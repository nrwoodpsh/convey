# 그래프DB(Neo4j) · Kafka 접속·조회 가이드

> 로컬 도커 스택 기준. 스택 기동: `scripts/up.sh` / 정지: `scripts/down.sh`.
> 비밀번호 등은 `.env`(기본값 표기). 운영 DB 직접 쓰기는 사람이(가드레일).

---

## 1. Neo4j (지식 그래프 — 종목·섹터·사건·관계)

### 접속 정보
| 항목 | 값 |
|:--|:--|
| 브라우저(웹 UI) | **http://localhost:7474** |
| Bolt(드라이버·cypher-shell) | `bolt://localhost:7687` |
| 사용자 | `neo4j` |
| 비밀번호 | `convey-dev-pw` (`.env`의 `NEO4J_AUTH=neo4j/…`) |

### 웹 UI로 보기
1. 브라우저에서 `http://localhost:7474` 접속.
2. Connect URL `bolt://localhost:7687`, ID `neo4j`, PW `convey-dev-pw` 입력.
3. 상단 입력창에 Cypher 실행(▶). 아래 예시 참고.

### CLI로 보기 (컨테이너)
```bash
docker compose exec neo4j cypher-shell -u neo4j -p convey-dev-pw \
  "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;"
```

### 자주 쓰는 Cypher
```cypher
// 관계 유형별 개수 (BELONGS_TO=섹터, HAS_EVENT=사건, COMPETES/SUPPLIES/AFFECTS=LLM 추출)
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;

// 특정 종목의 이웃 관계 (예: 삼성전자)
MATCH (s:Entity {name:'삼성전자'})-[r]->(o) RETURN s.name, type(r), o.name;

// 종목→섹터 (BELONGS_TO)
MATCH (s)-[:BELONGS_TO]->(sec) RETURN s.name, sec.name LIMIT 25;

// 종목→사건 (HAS_EVENT: 실적·공시·급등락 등)
MATCH (s)-[:HAS_EVENT]->(e) RETURN s.name, e.name LIMIT 25;

// 경쟁 구도 (COMPETES)
MATCH (a)-[:COMPETES]->(b) RETURN a.name, b.name;

// 전체 그래프 시각화(상위 100개 관계) — 웹 UI에서 그래프로 렌더
MATCH p=()-[r]->() RETURN p LIMIT 100;

// 근거 기사 id가 붙은 관계(가드레일: 무출처 없음) 확인
MATCH ()-[r]->() RETURN type(r), r.source_article_id LIMIT 10;
```
> 노드 라벨: `:Entity`(모든 엔티티), `:Stock`(종목명·ticker 속성). 관계는 근거(`source_article_id`)에 결속.

---

## 2. Kafka (이벤트 버스)

### 접속 정보
| 항목 | 값 |
|:--|:--|
| **kafka-ui(웹 UI)** | **http://localhost:8090** |
| 호스트 부트스트랩(외부) | `localhost:29092` |
| 컨테이너 내부 | `kafka:9092` |

### 토픽 (파이프라인 흐름)
```
market.ticks       시세(market-feed → research)
research.ingested  기사·공시(news-feed → research: 저장·그래프)
research.macro     거시지표(news-feed → research)
issue.selected     이슈 선별(issue-detector → content 자동양산)
content.generate   생성 요청(content 자기 큐 → consumer)
media.assemble     합성 요청(content → video-assembly)
content.assembled  합성 완료(video-assembly → content, fan-in)
content.ready      완성(내부 상태) · content.approved  발행 승인
```

### 웹 UI로 보기 (kafka-ui)
1. `http://localhost:8090` 접속(로그인 없음).
2. 좌측 **Topics** → 토픽 선택 → **Messages** 탭에서 실시간/과거 메시지 확인.
3. **Consumers** 탭에서 컨슈머 그룹 랙(lag) 확인(밀림 여부).

### CLI로 보기 (컨테이너)
```bash
# 토픽 목록
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# 특정 토픽 메시지 엿보기(최근 3건)
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic content.ready --from-beginning --max-messages 3

# 실시간 관찰(멈추려면 Ctrl+C)
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic research.ingested
```

---

## 3. (참고) Postgres — 사실 데이터

| 항목 | 값 |
|:--|:--|
| 접속 | `localhost:5432` · user `app` · pass `app` |
| DB | `research_db`(articles·price_ticks·macro_indicators) · `content_db`(generation_jobs·scripts·contents) |

```bash
# 완성 쇼츠 목록
docker compose exec postgres psql -U app -d content_db \
  -c "select j.id,j.status,j.topic,c.mp4_path from generation_jobs j left join contents c on c.job_id=j.id order by j.id desc limit 10;"
# 오늘자 기사
docker compose exec postgres psql -U app -d research_db \
  -c "select id,title,tickers,published_at from articles order by published_at desc limit 10;"
```
> GUI(DBeaver·TablePlus)면 접속 시 **Database에 `research_db` 또는 `content_db`를 지정**해야 테이블이 보인다(기본 `app`/`postgres` DB는 비어 있음).

---

## 4. 데이터 초기화 (테스트 정리)
```bash
scripts/reset-data.sh          # 잡·영상만(기사·그래프 유지)
scripts/reset-data.sh --all    # 기사·시세·그래프까지 전부(피드가 재수집)
docker compose down -v         # 볼륨까지 완전 초기화(스키마는 Alembic 재생성)
```
