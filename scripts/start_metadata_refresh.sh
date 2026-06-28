#!/usr/bin/env bash
# Start a detached MusicBrainz metadata refresh on the server (long-running).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONTAINER_NAME="${METADATA_REFRESH_CONTAINER:-music-review-metadata-refresh}"
MODE="${METADATA_REFRESH_MODE:-update}"
STATE_FILE="${ROOT_DIR}/data/.metadata_refresh.state"

if [[ "$MODE" != "update" && "$MODE" != "overwrite" ]]; then
  echo "Unsupported METADATA_REFRESH_MODE=${MODE} (use: update or overwrite)." >&2
  exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Metadata refresh is already running (container: ${CONTAINER_NAME})."
  echo "Monitor with: docker logs -f ${CONTAINER_NAME}"
  exit 0
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

if [[ "$MODE" == "overwrite" ]]; then
  FETCH_CMD="python -m music_review.pipeline.enrichment.fetch_metadata --overwrite"
else
  FETCH_CMD="python -m music_review.pipeline.enrichment.fetch_metadata --update"
fi

echo "Building metadata refresh image..."
docker compose --profile jobs build music-review-metadata-refresh

echo "Starting detached metadata refresh (mode=${MODE})..."
docker compose --profile jobs run -d \
  --name "$CONTAINER_NAME" \
  music-review-metadata-refresh \
  bash -lc "set -euo pipefail; ${FETCH_CMD}; python -m music_review.pipeline.enrichment.artist_genres --artist-profiles-output data/artist_genres.json --imputed-metadata-output data/metadata_imputed.jsonl; python -m music_review.pipeline.enrichment.reference_imputation"

CONTAINER_ID="$(docker ps -q --filter "name=^${CONTAINER_NAME}$")"
cat >"$STATE_FILE" <<EOF
container_name=${CONTAINER_NAME}
container_id=${CONTAINER_ID}
started_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mode=${MODE}
EOF

echo "Metadata refresh started."
echo "  container: ${CONTAINER_NAME}"
echo "  mode:      ${MODE}"
echo "  logs:      docker logs -f ${CONTAINER_NAME}"
echo "  outputs:   data/metadata.jsonl, data/metadata_imputed.jsonl, data/artist_genres.json"
