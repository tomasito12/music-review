#!/usr/bin/env bash
# Verify the production frontend nginx container serves its root page.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVICE="${DEPLOY_FRONTEND_SERVICE:-frontend}"
MAX_ATTEMPTS="${DEPLOY_HEALTH_ATTEMPTS:-30}"
SLEEP_SECONDS="${DEPLOY_HEALTH_SLEEP_SECONDS:-2}"

log() {
  printf '[deploy-health] %s\n' "$*"
}

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if docker compose exec -T "$SERVICE" wget -q -O /dev/null http://127.0.0.1/; then
    log "Frontend healthy on attempt ${attempt}/${MAX_ATTEMPTS}"
    exit 0
  fi

  log "Waiting for frontend (attempt ${attempt}/${MAX_ATTEMPTS})..."
  if ! docker compose ps "$SERVICE" 2>/dev/null | grep -Eq 'Up|running'; then
    log "Service ${SERVICE} is not running; recent logs:"
    docker compose logs --no-color --tail 80 "$SERVICE" || true
  fi

  sleep "$SLEEP_SECONDS"
done

log "Frontend health check failed after ${MAX_ATTEMPTS} attempts"
docker compose logs --no-color --tail 120 "$SERVICE" || true
exit 1
