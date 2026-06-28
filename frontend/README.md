# Plattenradar Frontend

React/Vite shell for the Plattenradar web frontend.

## Prerequisites

- Node.js **22.12+** (see `.node-version` in the repo root)
- Corepack enabled once: `corepack enable`
- pnpm version pinned via `packageManager` in this `package.json`

Hatch wraps the same commands from the project root (`hatch run frontend`, etc.).

## Commands

```bash
pnpm install
pnpm dev
pnpm test
pnpm build
pnpm screenshot
```

The dev server defaults to `http://127.0.0.1:5173`. The API defaults to
`http://127.0.0.1:8000` (start with `hatch run api` from the repo root).

### Screenshots

First-time setup for visual capture:

```bash
hatch run frontend-playwright-install
hatch run frontend-screenshot-live      # regression vs frontend/tests/visual/reference/
hatch run frontend-screenshot-update    # refresh reference PNGs after layout changes
hatch run frontend-screenshot           # mock/manual captures -> frontend/screenshots/
```

The live regression runner (`scripts/run_live_screenshots.py`) starts the visual
fixture API and Vite together. Manual mock PNG exports still land in
`frontend/screenshots/` (gitignored).

## Local full-stack

```bash
# Terminal 1 (repo root)
hatch run api

# Terminal 2 (repo root)
hatch run frontend-install
hatch run frontend
```

## Current Scope

This is a shell MVP, not a full Streamlit replacement yet. It includes:

- global app shell and navigation,
- welcome screen,
- mocked `Aktuell` result screen,
- API-backed `Entdecken` result screen for temporary taste profiles,
- editorial recommendation cards,
- music profile setup shell with broad-category, detail-style, and preset selection,
- playlist generator shell,
- auth dialog shell,
- typed API client foundation.

Optional env override for the API base URL: `VITE_API_BASE_URL` (not required
for local dev; the client defaults to `http://127.0.0.1:8000`).
