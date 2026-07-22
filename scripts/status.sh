#!/usr/bin/env bash
# CONVEY 스택 상태 + 헬스체크. HTTP 서비스만 /health 노출(워커는 Kafka 전용, HTTP 없음).
set -uo pipefail
cd "$(dirname "$0")/.."
GATEWAY_PORT="${GATEWAY_PORT:-8080}"

echo "=== 컨테이너 상태 ==="
docker compose ps --format '  {{.Service}}\t{{.State}}\t{{.Status}}'

echo; echo "=== 헬스체크 (HTTP 서비스) ==="
# 게이트웨이는 호스트 노출(8080). 나머지 HTTP 서비스는 컨테이너 내부에서 확인.
printf '  %-16s ' "gateway(:${GATEWAY_PORT})"
curl -fsS "http://localhost:${GATEWAY_PORT}/health" 2>/dev/null && echo || echo "DOWN"
for svc in research content agent llm-inference publishing issue-detector sample-domain; do
  printf '  %-16s ' "$svc"
  docker compose exec -T "$svc" python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health').read().decode())" 2>/dev/null || echo "DOWN/HTTP없음"
done
echo "  (news-feed·market-feed·video-assembly = Kafka 워커 — HTTP/헬스 엔드포인트 없음)"
