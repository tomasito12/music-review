#!/usr/bin/env bash
# Start a detached artist-image batch job on the server (long-running).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONTAINER_NAME="${ARTIST_IMAGE_BATCH_CONTAINER:-music-review-artist-image-batch}"
QUEUE="${ARTIST_IMAGE_QUEUE:-all}"
LOG_DIR="${ROOT_DIR}/logs"
STATE_FILE="${ROOT_DIR}/data/.artist_image_batch.state"

mkdir -p "$LOG_DIR"

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Artist image batch is already running (container: ${CONTAINER_NAME})."
  echo "Monitor with: docker logs -f ${CONTAINER_NAME}"
  exit 0
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Building artist image batch image..."
docker compose --profile jobs build music-review-artist-images

echo "Starting detached artist image batch (queue=${QUEUE})..."
docker compose --profile jobs run -d \
  --name "$CONTAINER_NAME" \
  music-review-artist-images \
  python -m music_review.pipeline.enrichment.artist_image_batch_cli \
    --missing-only \
    --all \
    --queue "$QUEUE" \
    --download \
    --report data/artist_image_batch_report.json \
    -v

CONTAINER_ID="$(docker ps -q --filter "name=^${CONTAINER_NAME}$")"
cat >"$STATE_FILE" <<EOF
container_name=${CONTAINER_NAME}
container_id=${CONTAINER_ID}
started_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
queue=${QUEUE}
EOF

echo "Artist image batch started."
echo "  container: ${CONTAINER_NAME}"
echo "  logs:      docker logs -f ${CONTAINER_NAME}"
echo "  report:    data/artist_image_batch_report.json (written when the job finishes)"
