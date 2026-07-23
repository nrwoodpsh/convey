#!/usr/bin/env bash
# 그래프 백필(㉕/A3) — 기존 기사에서 종목→섹터 엣지 재생성. 사람이 실행(운영 DB 쓰기).
# 결정론적(LLM 불필요). 실시간 관계추출과 별개로 과거 기사를 그래프에 채운다.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "▶ 그래프 백필(종목→섹터 엣지) 실행…"
docker compose exec -T research python -m app.backfill
echo "▶ 현재 그래프 관계 수:"
docker compose exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-convey-dev-pw}" \
  "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;" 2>/dev/null || true
