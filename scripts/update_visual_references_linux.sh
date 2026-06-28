#!/usr/bin/env bash
# Regenerate committed visual references on Linux (same renderer as GitHub Actions).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${PLAYWRIGHT_DOCKER_IMAGE:-mcr.microsoft.com/playwright:v1.61.1-noble}"

docker run --rm \
  -v "${ROOT}:/work" \
  -w /work \
  -e CI=true \
  "${IMAGE}" \
  bash -lc "
    set -euo pipefail
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv curl fonts-liberation fonts-dejavu-core
    pip install --quiet hatch uv
    hatch config set installer uv
    corepack enable
    corepack prepare pnpm@10.12.1 --activate
    hatch run frontend-install
    hatch run frontend-screenshot-update
  "
