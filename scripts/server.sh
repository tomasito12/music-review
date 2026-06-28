#!/usr/bin/env bash
# SSH helper for production server operations (read + write).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
if [[ -f "$ROOT_DIR/.env.server" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.env.server"
  set +a
fi

SERVER_USER="${MUSIC_REVIEW_SYNC_USER:-deploy}"
SERVER_HOST="${MUSIC_REVIEW_SYNC_HOST:-167.233.138.166}"
SERVER_PATH="${MUSIC_REVIEW_SYNC_PATH:-/srv/music-review}"
SSH_KEY="${MUSIC_REVIEW_SYNC_KEY:-$HOME/.ssh/music_review_deploy}"
SSH_PORT="${MUSIC_REVIEW_SYNC_PORT:-22}"
DRY_RUN="${MUSIC_REVIEW_SERVER_DRY_RUN:-false}"

HOURLY_CRON_MARKER="music-review-managed"
LOG_UPDATE="logs/hourly-update.log"
CONTAINER_BATCH="music-review-artist-image-batch"
CONTAINER_METADATA="music-review-metadata-refresh"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/server.sh <command> [options]

Read-only:
  status                 Docker, cron, latest review id, data mtimes
  logs update|batch|metadata [LINES]
  ssh                    Open an interactive SSH session
  exec <remote command>  Run one shell command on the server

Write (production changes):
  prod-update            Scrape new reviews + enrich metadata (docker job)
  install-cron           Install cron from deploy/production.crontab (IaC)
  install-hourly-cron    Alias for install-cron
  start-artist-image-batch
                         Start detached artist-image batch on the server
  start-metadata-refresh [overwrite]
                         Start detached metadata refresh on the server
  compose <args...>      Run docker compose on the server (e.g. compose ps)

Options:
  --dry-run              Print remote commands without executing them
  -h, --help             Show this help

Environment (see .env.server.example):
  MUSIC_REVIEW_SYNC_USER, MUSIC_REVIEW_SYNC_HOST, MUSIC_REVIEW_SYNC_PATH
  MUSIC_REVIEW_SYNC_KEY, MUSIC_REVIEW_SYNC_PORT
  MUSIC_REVIEW_SERVER_DRY_RUN=true   Same as --dry-run

Data sync (local):
  ./sync_data.sh pull|push   Separate script; do not push during long batch jobs.

GitHub Actions (preferred for code deploy):
  gh workflow run Deploy --field branch=main --field run_update=true
  gh workflow run "Artist image batch"
  gh workflow run "Metadata refresh"
USAGE
}

log() {
  printf '[server] %s\n' "$*"
}

fail() {
  printf '[server] ERROR: %s\n' "$*" >&2
  exit 1
}

build_ssh_base() {
  SSH_BASE_ARGS=(-p "$SSH_PORT" -o IdentitiesOnly=yes)
  if [[ -f "$SSH_KEY" ]]; then
    SSH_BASE_ARGS+=(-i "$SSH_KEY")
  fi
}

run_ssh() {
  build_ssh_base
  if [[ "$DRY_RUN" == true ]]; then
    log "DRY_RUN ssh ${SSH_BASE_ARGS[*]} ${SERVER_USER}@${SERVER_HOST} $*"
    return 0
  fi
  ssh "${SSH_BASE_ARGS[@]}" "${SERVER_USER}@${SERVER_HOST}" "$@"
}

run_remote_script() {
  local script_name="$1"
  shift
  local remote_cmd="cd $(printf '%q' "$SERVER_PATH") && ./scripts/${script_name}"
  if (($# > 0)); then
    remote_cmd+=" $(printf '%q ' "$@")"
  fi
  run_ssh "bash -lc $(printf '%q' "$remote_cmd")"
}

cmd_status() {
  run_ssh "bash -lc $(printf '%q' "
    set -euo pipefail
    cd '$SERVER_PATH'
    echo '=== host/path ==='
    echo \"\$(hostname) $SERVER_PATH\"
    echo '=== docker ==='
    docker compose ps -a 2>/dev/null || docker ps -a --filter name=music-review
    echo '=== crontab (deploy user) ==='
    crontab -l 2>/dev/null | grep -E 'music-review-managed|prod-update' || echo '(no music-review cron entries)'
    echo '=== reviews.jsonl ==='
    if [[ -f data/reviews.jsonl ]]; then
      python3 - <<'PY'
import json
from pathlib import Path
max_id = 0
count = 0
path = Path('data/reviews.jsonl')
for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
    if not line.strip():
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        continue
    count += 1
    max_id = max(max_id, int(row.get('id', 0)))
print(f'parsed={count} max_review_id={max_id}')
PY
      stat -c 'mtime=%y size=%s' data/reviews.jsonl 2>/dev/null || stat -f 'mtime=%Sm size=%z' data/reviews.jsonl
    else
      echo '(missing)'
    fi
    echo '=== artist images ==='
    if [[ -d data/artist_images ]]; then
      echo \"jpg_count=\$(find data/artist_images -maxdepth 1 -name '*.jpg' | wc -l | tr -d ' ')\"
    fi
    echo '=== recent logs ==='
    for f in logs/hourly-update.log logs/artist-image-batch.log; do
      if [[ -f \"\$f\" ]]; then
        echo \"-- tail \$f --\"
        tail -n 3 \"\$f\"
      fi
    done
  ")"
}

cmd_logs() {
  local target="${1:-update}"
  local lines="${2:-40}"
  local log_file
  case "$target" in
    update) log_file="$LOG_UPDATE" ;;
    batch) log_file="logs/artist-image-batch.log" ;;
    metadata) log_file="logs/metadata-refresh.log" ;;
    *)
      fail "Unknown log target: $target (use update, batch, or metadata)"
      ;;
  esac
  run_ssh "bash -lc $(printf '%q' "
    cd '$SERVER_PATH'
    if docker ps --format '{{.Names}}' | grep -qx '$CONTAINER_BATCH'; then
      echo '=== docker logs $CONTAINER_BATCH (last $lines) ==='
      docker logs --tail '$lines' '$CONTAINER_BATCH' 2>&1 || true
    fi
    if [[ -f '$log_file' ]]; then
      echo '=== file $log_file (last $lines) ==='
      tail -n '$lines' '$log_file'
    else
      echo '(no log file at $log_file)'
    fi
  ")"
}

cmd_prod_update() {
  log "Running production update on ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}"
  run_ssh "bash -lc $(printf '%q' "
    set -euo pipefail
    cd '$SERVER_PATH'
    mkdir -p logs
    docker compose --profile jobs run --rm music-review-update 2>&1 | tee -a '$LOG_UPDATE'
  ")"
}

cmd_install_cron() {
  log "Installing production cron from deploy/production.crontab on ${SERVER_USER}@${SERVER_HOST}"
  if [[ "$DRY_RUN" == true ]]; then
    run_ssh "bash -lc $(printf '%q' "
      cd '$SERVER_PATH'
      DEPLOY_PATH='$SERVER_PATH' CRONTAB_DRY_RUN=true ./scripts/install_production_cron.sh
    ")"
    return 0
  fi
  run_remote_script "install_production_cron.sh"
}

cmd_compose() {
  if (($# == 0)); then
    fail "Usage: ./scripts/server.sh compose <docker compose args...>"
  fi
  local remote_args
  remote_args="$(printf '%q ' "$@")"
  run_ssh "bash -lc $(printf '%q' "cd '$SERVER_PATH' && docker compose $remote_args")"
}

main() {
  local dry_run=false

  if (($# == 0)); then
    usage
    exit 1
  fi

  while (($# > 0)); do
    case "$1" in
      --dry-run)
        dry_run=true
        DRY_RUN=true
        shift
        ;;
      -h|--help|help)
        usage
        exit 0
        ;;
      status)
        cmd_status
        exit 0
        ;;
      logs)
        shift
        cmd_logs "${1:-update}" "${2:-40}"
        exit 0
        ;;
      ssh)
        if [[ "$DRY_RUN" == true ]]; then
          log "DRY_RUN: would open ssh to ${SERVER_USER}@${SERVER_HOST}"
          exit 0
        fi
        build_ssh_base
        exec ssh "${SSH_BASE_ARGS[@]}" "${SERVER_USER}@${SERVER_HOST}"
        ;;
      exec)
        shift
        (($# > 0)) || fail "Usage: ./scripts/server.sh exec <remote command>"
        run_ssh "$@"
        exit 0
        ;;
      prod-update)
        cmd_prod_update
        exit 0
        ;;
      install-cron|install-hourly-cron)
        cmd_install_cron
        exit 0
        ;;
      start-artist-image-batch)
        run_remote_script "start_artist_image_batch.sh"
        exit 0
        ;;
      start-metadata-refresh)
        shift
        local mode="${1:-}"
        if [[ "$mode" == "overwrite" ]]; then
          run_remote_script "start_metadata_refresh.sh" "overwrite"
        else
          run_remote_script "start_metadata_refresh.sh"
        fi
        exit 0
        ;;
      compose)
        shift
        cmd_compose "$@"
        exit 0
        ;;
      *)
        fail "Unknown command: $1 (run ./scripts/server.sh --help)"
        ;;
    esac
  done
}

main "$@"
