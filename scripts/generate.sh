#!/usr/bin/env bash
# 쇼츠 1건 생성 → 완성 mp4를 호스트 out/로 추출. 스택이 떠 있어야 함(scripts/up.sh).
# 사용: scripts/generate.sh [ticker]   (기본 005930)
# 산출: out/convey-<ticker>-job<id>.mp4  ← 이 파일을 사람이 YouTube에 업로드
set -euo pipefail
cd "$(dirname "$0")/.."
TICKER="${1:-005930}"
mkdir -p out

echo "[generate] ticker=$TICKER 생성 트리거..."
OUT="$(python scripts/trigger_generate.py "$TICKER")" || { echo "$OUT"; echo "[generate] ✗ 생성 실패"; exit 1; }
echo "$OUT"
MP4_PATH="$(echo "$OUT" | sed -n 's/^MP4=//p')"
JOB="$(echo "$OUT" | sed -n 's/^JOB=//p')"
[ -n "$MP4_PATH" ] || { echo "[generate] ✗ mp4 경로 없음"; exit 1; }

DEST="out/convey-${TICKER}-job${JOB}.mp4"
echo "[generate] 미디어 볼륨에서 추출: $MP4_PATH → $DEST"
docker compose cp "content:${MP4_PATH}" "$DEST"
ls -lh "$DEST" | awk '{print "  "$5" "$9}'
echo "[generate] ✓ 완료 — $DEST (YouTube 수동 업로드용)"
