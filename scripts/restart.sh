#!/usr/bin/env bash
# CONVEY 스택 한방 재기동 — 정지 후 재빌드·기동. Jenkins 배포 엔트리포인트.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[restart] === 정지 ==="
bash scripts/down.sh
echo "[restart] === 기동 ==="
bash scripts/up.sh
echo "[restart] ✓ 재기동 완료."
