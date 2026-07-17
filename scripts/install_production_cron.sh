#!/usr/bin/env bash
# Install or refresh production cron entries from deploy/production.crontab.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CRON_TEMPLATE="${ROOT_DIR}/deploy/production.crontab"
DEPLOY_PATH="${DEPLOY_PATH:-${MUSIC_REVIEW_SYNC_PATH:-$ROOT_DIR}}"
CRONTAB_DRY_RUN="${CRONTAB_DRY_RUN:-false}"

MANAGED_BEGIN="# music-review-managed-begin"
MANAGED_END="# music-review-managed-end"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/install_production_cron.sh

Installs cron lines from deploy/production.crontab on the current user crontab.
Existing music-review-managed blocks are replaced idempotently; other cron lines
are preserved.

Environment:
  DEPLOY_PATH          Server repo path (default: cwd or MUSIC_REVIEW_SYNC_PATH)
  CRONTAB_DRY_RUN=true Print merged crontab instead of installing
  CRONTAB_TARGET=path  Write merged crontab to a file (for tests) instead of crontab -e
USAGE
}

fail() {
  printf '[install-cron] ERROR: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[install-cron] %s\n' "$*"
}

strip_managed_block() {
  awk -v begin="$MANAGED_BEGIN" -v end="$MANAGED_END" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  '
}

strip_legacy_hourly_update_entries() {
  awk '
    /docker compose/ && /music-review-update/ && /hourly-update\.log/ { next }
    /Managed production cron for music-review/ { next }
    /Placeholder .* is replaced by scripts\/install_production_cron\.sh/ { next }
    /Do not edit crontab manually on the server/ { next }
    { print }
  '
}

render_managed_block() {
  if [[ ! -f "$CRON_TEMPLATE" ]]; then
    fail "Missing cron template: $CRON_TEMPLATE"
  fi
  sed "s|__DEPLOY_PATH__|${DEPLOY_PATH}|g" "$CRON_TEMPLATE"
}

merge_crontab() {
  local current=""
  if [[ -n "${CRONTAB_TARGET:-}" && -f "$CRONTAB_TARGET" ]]; then
    current="$(cat "$CRONTAB_TARGET")"
  else
    current="$(crontab -l 2>/dev/null || true)"
  fi
  printf '%s\n' "$current" | strip_managed_block | strip_legacy_hourly_update_entries
  render_managed_block
}

install_crontab() {
  local merged
  merged="$(merge_crontab)"
  if [[ "$CRONTAB_DRY_RUN" == true ]]; then
    log "DRY_RUN merged crontab:"
    printf '%s\n' "$merged"
    return 0
  fi
  if [[ -n "${CRONTAB_TARGET:-}" ]]; then
    printf '%s\n' "$merged" >"$CRONTAB_TARGET"
    log "Wrote merged crontab to $CRONTAB_TARGET"
    return 0
  fi
  printf '%s\n' "$merged" | crontab -
  log "Installed production cron for DEPLOY_PATH=$DEPLOY_PATH"
  crontab -l
}

main() {
  case "${1:-}" in
    -h|--help|help)
      usage
      exit 0
      ;;
    "")
      install_crontab
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
}

main "$@"
