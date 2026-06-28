#!/usr/bin/env bash
# Ensure the pinned pnpm version is available, then exec pnpm.
set -euo pipefail

PNPM_VERSION="10.12.1"

if ! command -v pnpm >/dev/null 2>&1; then
  corepack enable
  corepack prepare "pnpm@${PNPM_VERSION}" --activate
fi

exec pnpm "$@"
