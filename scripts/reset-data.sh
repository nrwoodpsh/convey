#!/usr/bin/env bash
# CONVEY 데이터 초기화 — 테스트로 쌓인 잡·영상 정리. 사람이 실행(가드레일: 운영 DB는 사람이).
#
#   ./scripts/reset-data.sh          잡·시나리오·완성본 + 영상 파일만 삭제(기사·시세는 유지)
#   ./scripts/reset-data.sh --all    위 + 기사·시세·거시·지식그래프까지 전부 삭제(피드가 다시 수집)
#   ./scripts/reset-data.sh --nuke   docker compose down -v (모든 볼륨 파괴) 안내만 출력
#
# 로컬 도커 전용. 되돌릴 수 없음.
set -euo pipefail
cd "$(dirname "$0")/.."

PG="docker compose exec -T postgres psql -U app"
MODE="${1:-content}"

if [ "$MODE" = "--nuke" ]; then
  echo "전체 초기화(볼륨 파괴)는 아래를 직접 실행하세요:"
  echo "  docker compose down -v && ./scripts/up.sh"
  echo "(Postgres·Neo4j·영상 볼륨 모두 삭제 → 스키마는 Alembic이 재생성, 기사는 피드가 재수집)"
  exit 0
fi

echo "▶ content_db 잡·시나리오·완성본 삭제…"
$PG -d content_db -c "TRUNCATE generation_jobs, scripts, contents RESTART IDENTITY CASCADE;" >/dev/null

echo "▶ 영상 파일(media 볼륨) 삭제…"
docker compose exec -T content sh -c 'rm -f /data/media/*.mp4 /data/media/*.png /data/media/*.mp3 /data/media/*.wav 2>/dev/null || true'

if [ "$MODE" = "--all" ]; then
  echo "▶ research_db 기사·시세·거시 삭제…"
  $PG -d research_db -c "TRUNCATE articles, price_ticks, macro_indicators RESTART IDENTITY CASCADE;" >/dev/null
  echo "▶ Neo4j 지식그래프 삭제…"
  docker compose exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-convey-dev-pw}" "MATCH (n) DETACH DELETE n;" >/dev/null 2>&1 || \
    echo "  (Neo4j 비밀번호가 다르면 수동: MATCH (n) DETACH DELETE n)"
  echo "  ※ 기사·시세는 news-feed·market-feed가 다시 수집합니다."
fi

echo "✔ 초기화 완료. 남은 건수:"
$PG -d content_db -c "select 'jobs' t,count(*) from generation_jobs union all select 'contents',count(*) from contents;" 2>/dev/null || true
