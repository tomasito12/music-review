# Deployment

## GitHub Actions secrets

Create these repository secrets under `Settings -> Secrets and variables -> Actions`:

- `DEPLOY_HOST`: server hostname or IP address.
- `DEPLOY_USER`: SSH user on the server.
- `DEPLOY_SSH_KEY`: private SSH key allowed to log in as `DEPLOY_USER`.
- `DEPLOY_PATH`: absolute path to this repository on the server.
- `DEPLOY_PORT`: SSH port. Optional when the server uses port `22`.

Keep production `.env` and `data/` files on the server. The GitHub workflow does
not upload local secrets or data.

## Server prerequisites

- The repository is already cloned at `DEPLOY_PATH`.
- Docker and Docker Compose are installed for `DEPLOY_USER`.
- The server checkout has a production `.env` file.
- `DEPLOY_USER` can run `git fetch`, `docker compose build`, and
  `docker compose up -d`.

## Manual deploy

Open the `Deploy` workflow in GitHub Actions, choose the branch, and run it.
The workflow verifies lint/tests first, then deploys over SSH:

1. Fetch and fast-forward the selected branch on the server.
2. Rebuild the `music-review` API image and the `frontend` static site image.
3. Restart `music-review`, `frontend`, and `caddy`.
4. Install production cron from `deploy/production.crontab` (idempotent).
5. Optionally run `music-review-update`.
6. Check the API via `./scripts/check_deploy_api_health.sh` (host curl on port 8000 with retries/logs) and the frontend nginx root via `./scripts/check_deploy_frontend_health.sh`.

Public traffic at `https://plattenradar.de` is served by Caddy:

- `/v1/*`, `/health`, and OpenAPI docs go to the FastAPI container on port 8000.
- All other paths go to the React frontend (nginx with SPA fallback).

Local Streamlit development remains available via `hatch run dashboard`; it is
no longer part of the production Docker stack.

## Artist image batch (long-running)

Use the **Artist image batch** GitHub Actions workflow to start a detached job on
the server. The workflow exits after the container starts; monitor with
`docker logs -f music-review-artist-image-batch`.

Manual start on the server:

```bash
./scripts/start_artist_image_batch.sh
```

## Metadata refresh (long-running)

Use the **Metadata refresh** GitHub Actions workflow to re-fetch MusicBrainz
metadata for all reviews, then rebuild `metadata_imputed.jsonl` and
`artist_genres.json`. The workflow exits after the container starts; monitor with
`docker logs -f music-review-metadata-refresh`.

Manual start on the server:

```bash
./scripts/start_metadata_refresh.sh
METADATA_REFRESH_MODE=overwrite ./scripts/start_metadata_refresh.sh
```

See `docs/metadata-refresh.md` for details.

## Full database update (long-running)

Use the **Update database** GitHub Actions workflow to run `update_database.py`
on the server (scrape, metadata, imputation, graph, DQ). Optional inputs:
`metadata_update`, `skip_reviews`, `skip_graph_affinities`, `recluster_communities`.

```bash
gh workflow run "Update database" --field branch=main
```

Monitor with `docker logs -f music-review-update-db` or
`./scripts/server.sh logs update-db`.

Manual start on the server:

```bash
UPDATE_DB_METADATA_UPDATE=true ./scripts/start_update_db.sh
```

## Server operations (SSH)

Local helper: `./scripts/server.sh` (configure via `.env.server` from `.env.server.example`).

| Command | Purpose |
|---------|---------|
| `./scripts/server.sh status` | Cron, Docker, max review id |
| `./scripts/server.sh prod-update` | Scrape + enrich new reviews |
| `./scripts/server.sh install-cron` | Apply `deploy/production.crontab` on server |
| `./scripts/server.sh start-artist-image-batch` | Detached image batch |
| `./scripts/server.sh start-metadata-refresh` | Detached metadata refresh |
| `./scripts/server.sh start-update-db` | Detached full database update |

Cron schedule lives in **`deploy/production.crontab`** and is reapplied on every GitHub **Deploy** run via `scripts/install_production_cron.sh`.
