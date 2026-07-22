# 운영 가이드 — 로컬/배포 구동·접속·생성

CONVEY 스택을 **한 방에 기동·정지·재기동**하고, DB/Kafka에 접속해 들여다보고, 쇼츠 1건을 뽑아 YouTube에 수동 업로드하기까지. Jenkins 배포 엔트리포인트도 여기 스크립트.

## 1. 스택 스크립트 (Jenkins용)

| 스크립트 | 하는 일 |
|:--|:--|
| `scripts/up.sh` | 이미지 빌드 + 기동 + 게이트웨이 헬스 대기(실패 시 non-zero). **ollama 컨테이너는 안 뜸**(네이티브 재사용). |
| `scripts/down.sh` | 컨테이너 정지·제거(**데이터 볼륨 보존**: pgdata·neo4jdata·media). |
| `scripts/restart.sh` | down → up. **배포 한 방 재기동.** |
| `scripts/status.sh` | 컨테이너 상태 + HTTP 서비스 헬스체크. |
| `scripts/generate.sh [ticker]` | 쇼츠 1건 생성 → `out/convey-<ticker>-job<id>.mp4` 추출(기본 005930). |

```bash
scripts/up.sh          # 기동
scripts/status.sh      # 상태·헬스
scripts/generate.sh 035420   # 쇼츠 생성 → out/
scripts/down.sh        # 정지
scripts/restart.sh     # 재기동(배포)
```
> 전제: Docker 실행 중, **네이티브 Ollama 기동 + `qwen3:14b` 보유**(`ollama list`), `.env`에 키 채움(`doc/ref/external-credentials.md`). DB 테이블은 컨테이너 기동 시 **Alembic 자동 마이그레이션**.

## 2. 헬스체크 — 도메인별

**HTTP 서비스(헬스 O)** — `GET /health` → `{"status":"ok"}`
| 서비스 | 접근 |
|:--|:--|
| **gateway** | 호스트 노출: `curl http://localhost:8080/health` (유일한 외부 진입점) |
| research · content · agent · llm-inference · publishing · issue-detector · sample-domain | 내부(게이트웨이 뒤). `docker compose exec <svc> curl -s localhost:8000/health` 또는 `scripts/status.sh` |

**Kafka 워커(헬스 X — HTTP 없음)**: `news-feed` · `market-feed` · `video-assembly`. 상태는 `docker compose ps` + 로그(`docker compose logs -f <svc>`)로 확인.

### 운영 대시보드 (브라우저 — ADR 0010)
- 접속: **`http://localhost:8091`** (content 직접 서빙, **무인증·로컬 전용** — gateway·Supabase 우회).
- 사용: 제목·종목 입력 → **생성 시작** → 목록에서 진행 상태(자동 폴링) → 완료 시 **재생**(9:16 미리보기).
- API: `POST /ui/generate` · `GET /ui/jobs` · `GET /ui/contents/{content_id}/video`(mp4·Range).
- 유튜브 업로드는 여전히 사람이 수동(§4). 운영 배포 시엔 8091 비노출 권장.

## 3. DB·Kafka 접속 정보

### Postgres (사실: 시세·기사·거시·잡·스크립트·완성본)
- 접속: `localhost:5432` · user `app` · pass `app`
- DB: `research_db`(articles·price_ticks·macro_indicators) · `content_db`(generation_jobs·scripts·contents) · `publishing_db`(publish_records) · `sample_db`
```bash
psql postgresql://app:app@localhost:5432/research_db -c "SELECT ticker,close,ts FROM price_ticks ORDER BY ts DESC LIMIT 5;"
psql postgresql://app:app@localhost:5432/content_db  -c "SELECT id,status,ticker,owner_id FROM generation_jobs ORDER BY id DESC LIMIT 5;"
# psql이 호스트에 없으면: docker exec -it py-msa-ai-starter-postgres-1 psql -U app -d research_db
```

### Neo4j (지식 그래프: 종목·관계·인과)
- Browser: `http://localhost:7474` · Bolt: `bolt://localhost:7687` · user `neo4j` · pass `convey-dev-pw`
```cypher
MATCH (s:Stock) RETURN s.name, s.ticker;                 // 종목 노드
MATCH (s:Entity {name:'삼성전자'})-[r]->(o) RETURN s.name,type(r),o.name;  // 관계
```
```bash
docker exec -it py-msa-ai-starter-neo4j-1 cypher-shell -u neo4j -p convey-dev-pw "MATCH (n) RETURN labels(n),count(*)"
```

### Kafka (이벤트 버스)
- 호스트 접속: `localhost:29092`(외부 리스너) · 내부: `kafka:9092` · **kafka-ui**: `http://localhost:8090`
- 토픽: `market.ticks` · `research.ingested` · `research.macro` · `content.generate` · `media.assemble` · `content.assembled` · `content.ready` · `content.approved` · `issue.selected`
```bash
docker exec -it py-msa-ai-starter-kafka-1 \
  kafka-console-consumer --bootstrap-server localhost:9092 --topic content.ready --from-beginning --max-messages 3
```

## 4. 쇼츠 생성 → YouTube 수동 업로드

```bash
scripts/generate.sh 035420      # issue.selected 발행 → 자동 생성 → ready → out/ 추출
# → out/convey-035420-job<id>.mp4  (h264 9:16 + 한국어 음성 + Pexels 배경 + 정확 차트)
```
- **발행(업로드)은 사람이** — 파이프라인은 완성본(mp4)까지만 자동(가드레일: 콘텐츠 자동 발행 금지). 생성된 `out/*.mp4`를 확인 후 YouTube에 직접 업로드.
- 종목별 배경: `_BROLL_MAP`(content). 시세 데이터 없는 종목은 스크립트 생성이 실패할 수 있음(pykrx 수집 후 재시도).
- **중복회피**: 같은 종목을 최근 1일 내 이미 생성했으면 자동 경로는 skip(수동 `POST /content/generate`는 무조건 생성).

## 5. 트러블슈팅
- `generate.sh` 타임아웃: `docker compose logs content agent research`로 스크립트/합성 단계 확인. 시세 없는 종목·Ollama 미기동이 흔한 원인.
- 게이트웨이 401: 인증(Supabase)은 보류(C2). 내부 검증은 로컬 JWKS 시뮬(`doc/summary/20260722-summary-gateway-e2e.md`).
- 전체 초기화(데이터 삭제): `docker compose down -v` (주의: DB·미디어 전부 삭제).
