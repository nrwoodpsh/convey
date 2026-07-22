#!/usr/bin/env bash
# CONVEY 스택 기동 — 인프라(PG·Neo4j·Kafka) + 앱(빌드 후 기동).
# ollama는 프로필로 격리되어 기동 안 함(네이티브 호스트 ollama 재사용, OLLAMA_HOST=host.docker.internal).
# Jenkins: 이 스크립트 하나로 빌드+기동+헬스게이트. 실패 시 non-zero 종료.
set -euo pipefail
cd "$(dirname "$0")/.."

GATEWAY_PORT="${GATEWAY_PORT:-8080}"

[ -f .env ] || { echo "[up] .env 없음 → .env.example 복사(키는 채워야 함)"; cp .env.example .env; }

echo "[up] 이미지 빌드 + 기동 (ollama 컨테이너 제외)..."
docker compose up -d --build

echo "[up] 게이트웨이 헬스 대기 (http://localhost:${GATEWAY_PORT}/health)..."
for i in $(seq 1 40); do
  if curl -fsS "http://localhost:${GATEWAY_PORT}/health" >/dev/null 2>&1; then
    echo "[up] gateway OK"
    break
  fi
  if [ "$i" -eq 40 ]; then
    echo "[up] ✗ gateway 헬스 실패 — 로그 확인:"; docker compose ps; exit 1
  fi
  sleep 2
done

echo "[up] 컨테이너 상태:"
docker compose ps --format '  {{.Service}}\t{{.State}}\t{{.Status}}'
echo "[up] ✓ 완료. 진입점: http://localhost:${GATEWAY_PORT}  · kafka-ui: http://localhost:${KAFKAUI_PORT:-8090}"
