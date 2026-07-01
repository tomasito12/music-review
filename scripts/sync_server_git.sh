#!/usr/bin/env bash
# Align the server checkout with origin/<branch> (discards local tracked edits).
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/sync_server_git.sh [BRANCH]

Sync the current repository to match origin/<branch> exactly.
Untracked files are kept; modified tracked files are reset.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

BRANCH="${1:-main}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository." >&2
  exit 1
fi

echo "Syncing server checkout to origin/${BRANCH}..."
git fetch --prune origin
git checkout "${BRANCH}"
git reset --hard "origin/${BRANCH}"
echo "Server checkout is now at $(git rev-parse --short HEAD)."
