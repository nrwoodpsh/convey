#!/usr/bin/env bash
# CONVEY 2차 개발 통합 스모크 — 커밋 전 로컬 한 바퀴 검증.
# 시나리오 원문: doc/ref/integration-scenario-phase2.md
# 실 외부키(YouTube refresh_token·Supabase 실프로젝트)는 범위 밖 — 폴백/게이트까지만.
#
# 실행:  bash scripts/smoke-phase2.sh   (전 스택 up 상태 전제)
set -uo pipefail
cd "$(dirname "$0")/.."

SR_PORT="${SCHEMA_REGISTRY_PORT:-8085}"
CN_PORT="${CONNECT_PORT:-8083}"
PROM_PORT="${PROMETHEUS_PORT:-9090}"
GRAF_PORT="${GRAFANA_PORT:-3000}"

PASS=0; FAIL=0; SKIP=0
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; PASS=$((PASS+1)); }
no(){ printf '  \033[31m✗\033[0m %s  \033[2m%s\033[0m\n' "$1" "${2:-}"; FAIL=$((FAIL+1)); }
sk(){ printf '  \033[33m·\033[0m %s  \033[2m(skip: %s)\033[0m\n' "$1" "$2"; SKIP=$((SKIP+1)); }
sec(){ printf '\n\033[1m%s\033[0m\n' "$1"; }
dex(){ docker compose exec -T "$1" python -c "$2" 2>/dev/null; }
# check "라벨" "출력" "성공토큰"  — 출력에 토큰이 있으면 통과(라벨+출력 전문 표시)
chk(){ if echo "$2" | grep -q "$3"; then ok "$1  ${2#* }"; else no "$1" "${2:-무응답}"; fi; }

sec "0 · 인프라 (P2·P3·P5)"
wal=$(docker compose exec -T postgres psql -U app -d postgres -tAc "SHOW wal_level;" 2>/dev/null | tr -d '[:space:]')
[ "$wal" = "logical" ] && ok "postgres wal_level=logical (Debezium 전제)" || no "wal_level" "→ '$wal' (기대 logical)"
curl -fsS "http://localhost:${SR_PORT}/subjects" >/dev/null 2>&1 && ok "Schema Registry 응답 (:$SR_PORT)" || no "Schema Registry" "미응답 (:$SR_PORT)"
if curl -fsS "http://localhost:${CN_PORT}/connectors" 2>/dev/null | grep -q content-outbox; then
  curl -fsS "http://localhost:${CN_PORT}/connectors/content-outbox/status" 2>/dev/null | grep -q '"state":"RUNNING"' \
    && ok "Debezium content-outbox 커넥터 RUNNING" || no "Debezium 커넥터" "RUNNING 아님"
else no "Debezium 커넥터" "content-outbox 미등록 (:$CN_PORT)"; fi

sec "1 · 수집 → 그래프 (research, 알파①)"
gs=$(dex content "import asyncio; from app import research_client; n,r=asyncio.run(research_client.fetch_graph_stats()); print('GRAPH_OK 노드=%d 관계=%d'%(n,r) if isinstance(n,int) else 'GRAPH_FAIL')")
chk "그래프 조회 체인" "${gs:-무응답}" "GRAPH_OK"

sec "2 · admin 설정 왕복 (㉝·㊳·㊴ — content 중계 CRUD)"
kv=$(dex content "
import httpx; c=httpx.Client(base_url='http://localhost:8000',timeout=15)
s=len(c.get('/ui/settings/stocks').json()); t=len(c.get('/ui/settings/templates').json())
r=c.post('/ui/settings/keywords',json={'term':'스모크테스트'}); k=r.json().get('id')
d=c.delete(f'/ui/settings/keywords/{k}').status_code if k else 0
print('ADMIN_OK 종목=%d 템플릿=%d 왕복=%s/%s'%(s,t,r.status_code,d) if r.status_code==200 and d==200 else 'ADMIN_FAIL')")
chk "설정 CRUD 왕복 (admin_db 반영)" "${kv:-무응답}" "ADMIN_OK"

sec "3 · 품질 지표 (㊵ 대시보드 백엔드)"
m=$(dex content "import httpx; d=httpx.get('http://localhost:8000/ui/metrics',timeout=15).json(); print('METRICS_OK 노드=%s 이슈=%s 완성잡=%s'%(d.get('graph_nodes'),d.get('issues_selected'),d.get('jobs_ready')) if 'graph_nodes' in d else 'METRICS_FAIL')")
chk "품질 지표 응답" "${m:-무응답}" "METRICS_OK"

sec "4 · 배경 라이브러리 섹터 매칭 (㊴)"
bg=$(dex video-assembly "
from app.background import match_background
a=[{'id':1,'name':'t','tags':['자동차'],'path':'/etc/hostname','kind':'image','license':'CC0','enabled':True}]
print('BG_OK 현대차→자동차 매칭·삼성전자 무관' if match_background(a,'005380') and match_background(a,'005930') is None else 'BG_FAIL')")
chk "섹터 태그 매칭" "${bg:-무응답}" "BG_OK"

sec "5 · 발행 아웃박스 배선 (㊶ C1 + ㊱ P3)"
ob=$(docker compose exec -T postgres psql -U app -d content_db -tAc "SELECT to_regclass('public.outbox');" 2>/dev/null | tr -d '[:space:]')
[ "$ob" = "outbox" ] && ok "content_db.outbox 테이블 존재 (트랜잭션 아웃박스)" || no "아웃박스 테이블" "$ob"

sec "6 · 이벤트 정석 (㊱ P2·P4·P5)"
curl -fsS "http://localhost:${SR_PORT}/subjects" 2>/dev/null | grep -q -- '-value' && ok "Avro subject 등록됨 (P2)" || sk "Avro subject" "아직 발행 이벤트 없음"
dlq=$(dex content "
import asyncio
from common.kafka import KafkaProducer, consume_reliable
async def bad(p): raise ValueError('smoke')
async def main():
    p=KafkaProducer('kafka:9092','smoke'); await p.start()
    await p.publish('smoke.p2.t',{'x':1}); await p.stop()
    t=asyncio.create_task(consume_reliable(topic='smoke.p2.t',group_id='smoke-g2',bootstrap='kafka:9092',handler=bad,retry_max=1))
    await asyncio.sleep(6); t.cancel()
    from confluent_kafka import Consumer; import time
    c=Consumer({'bootstrap.servers':'kafka:9092','group.id':'smoke-dlq2','auto.offset.reset':'earliest'}); c.subscribe(['smoke.p2.t.dlq'])
    hit=False; s=time.time()
    while time.time()-s<8:
        m=c.poll(1.0)
        if m and not m.error(): hit=True; break
    c.close(); print('DLQ_OK' if hit else 'DLQ_MISS')
asyncio.run(main())")
chk "P4 DLQ (실패 → *.dlq 도달)" "${dlq:-무응답}" "DLQ_OK"
if curl -fsS --data-urlencode 'query=sum(kafka_consumergroup_lag)' "http://localhost:${PROM_PORT}/api/v1/query" 2>/dev/null | grep -q '"result"'; then ok "P5 Prometheus consumer_lag 수집"; else sk "P5 Prometheus" "미기동 (:$PROM_PORT)"; fi
curl -fsS "http://localhost:${GRAF_PORT}/api/health" 2>/dev/null | grep -q '"database": "ok"' && ok "P5 Grafana 헬스" || sk "P5 Grafana" "미기동 (:$GRAF_PORT)"

sec "7 · 인증 코드 (㊶ C2 — 자체서명 JWKS, 실 Supabase는 pending)"
PYTHONPATH=libs/common python -m pytest libs/common/tests/test_supabase_auth.py -q >/dev/null 2>&1 \
  && ok "게이트웨이 JWKS 검증 7건 통과" || no "인증 단위" "test_supabase_auth 실패"

sec "8 · 단위·타입 회귀 (커밋 게이트)"
PYTHONPATH=libs/common python -m pytest libs/common/tests/ -q >/dev/null 2>&1 \
  && ok "common 단위(봉투·Avro·DLQ·인증)" || no "common 단위" "실패"
MYPYPATH=libs/common python -m mypy --strict --ignore-missing-imports libs/common/common/kafka.py >/dev/null 2>&1 \
  && ok "mypy --strict kafka.py 0" || no "mypy kafka.py" "오류"

printf '\n\033[1m결과\033[0m  \033[32m통과 %d\033[0m · \033[31m실패 %d\033[0m · \033[33m스킵 %d\033[0m\n' "$PASS" "$FAIL" "$SKIP"
echo "미완(외부키): YouTube refresh_token · Supabase 실프로젝트 — 2차 점검 후 진행"
[ "$FAIL" -eq 0 ]
