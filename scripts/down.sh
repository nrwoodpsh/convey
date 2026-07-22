#!/usr/bin/env bash
# CONVEY 스택 정지 — 컨테이너 중지·제거(데이터 볼륨 pgdata·neo4jdata·media는 보존).
# 데이터까지 삭제하려면: docker compose down -v  (주의: DB·미디어 전부 삭제)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[down] 스택 정지·제거 (볼륨 보존)..."
docker compose --profile ollama down
echo "[down] ✓ 완료. (데이터 볼륨 보존 — 재기동은 scripts/up.sh)"
