#!/usr/bin/env bash
# Wait for the production API to respond and print logs when it stays down.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVICE="${DEPLOY_API_SERVICE:-music-review}"
HEALTH_URL="${DEPLOY_API_HEALTH_URL:-http://127.0.0.1:8000/health}"
MAX_ATTEMPTS="${DEPLOY_HEALTH_ATTEMPTS:-30}"
SLEEP_SECONDS="${DEPLOY_HEALTH_SLEEP_SECONDS:-2}"

log() {
  printf '[deploy-health] %s\n' "$*"
}

log "Docker Compose status before API health check:"
docker compose ps -a || true

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if curl -sf "$HEALTH_URL" >/dev/null; then
    log "API healthy on attempt ${attempt}/${MAX_ATTEMPTS} (${HEALTH_URL})"
    exit 0
  fi

  log "Waiting for API (attempt ${attempt}/${MAX_ATTEMPTS})..."
  if ! docker compose ps "$SERVICE" 2>/dev/null | grep -Eq 'Up|running'; then
    log "Service ${SERVICE} is not running; recent logs:"
    docker compose logs --no-color --tail 80 "$SERVICE" || true
  fi

  sleep "$SLEEP_SECONDS"
done

log "API health check failed after ${MAX_ATTEMPTS} attempts"
docker compose logs --no-color --tail 120 "$SERVICE" || true
exit 1
