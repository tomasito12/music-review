#!/usr/bin/env bash
# Start a detached full database update on the server (long-running).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONTAINER_NAME="${UPDATE_DB_CONTAINER:-music-review-update-db}"
STATE_FILE="${ROOT_DIR}/data/.update_db.state"

UPDATE_ARGS=(-v)
if [[ "${UPDATE_DB_METADATA_UPDATE:-false}" == "true" ]]; then
  UPDATE_ARGS+=(--metadata-update)
fi
if [[ "${UPDATE_DB_SKIP_REVIEWS:-false}" == "true" ]]; then
  UPDATE_ARGS+=(--skip-reviews)
fi
if [[ "${UPDATE_DB_SKIP_GRAPH_AFFINITIES:-false}" == "true" ]]; then
  UPDATE_ARGS+=(--skip-graph-affinities)
fi
if [[ "${UPDATE_DB_RECLUSTER_COMMUNITIES:-false}" == "true" ]]; then
  UPDATE_ARGS+=(--recluster-communities)
fi

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Database update is already running (container: ${CONTAINER_NAME})."
  echo "Monitor with: docker logs -f ${CONTAINER_NAME}"
  exit 0
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Building update-db image..."
docker compose --profile jobs build music-review-update-db

quoted_args="$(printf '%q ' "${UPDATE_ARGS[@]}")"
echo "Starting detached database update..."
docker compose --profile jobs run -d \
  --name "$CONTAINER_NAME" \
  music-review-update-db \
  bash -lc "set -euo pipefail; python scripts/update_database.py ${quoted_args}"

CONTAINER_ID="$(docker ps -q --filter "name=^${CONTAINER_NAME}$")"
cat >"$STATE_FILE" <<EOF
container_name=${CONTAINER_NAME}
container_id=${CONTAINER_ID}
started_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
metadata_update=${UPDATE_DB_METADATA_UPDATE:-false}
skip_reviews=${UPDATE_DB_SKIP_REVIEWS:-false}
skip_graph_affinities=${UPDATE_DB_SKIP_GRAPH_AFFINITIES:-false}
recluster_communities=${UPDATE_DB_RECLUSTER_COMMUNITIES:-false}
EOF

echo "Database update started."
echo "  container: ${CONTAINER_NAME}"
echo "  logs:      docker logs -f ${CONTAINER_NAME}"
echo "  state:     ${STATE_FILE}"
