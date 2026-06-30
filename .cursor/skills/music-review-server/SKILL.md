---
name: music-review-server
description: >-
  Production server operations for music-review (Hetzner deploy@ host). Use when
  diagnosing or changing production data, Docker jobs, cron, logs, prod-update,
  artist-image batch, metadata refresh, or SSH to /srv/music-review.
---

# Music Review production server

## Default entry point

Always prefer **`./scripts/server.sh`** over hand-built `ssh` commands.

```bash
cp .env.server.example .env.server   # once, local only
./scripts/server.sh status
./scripts/server.sh logs update
./scripts/server.sh prod-update
```

Set `MUSIC_REVIEW_SERVER_DRY_RUN=true` or pass `--dry-run` before write commands to preview remote actions.

## Connection defaults

| Setting | Default |
|---------|---------|
| Host | `167.233.138.166` |
| User | `deploy` |
| Repo path | `/srv/music-review` |
| SSH key | `~/.ssh/music_review_deploy` |

Override via `.env.server` or `MUSIC_REVIEW_SYNC_*` variables (same as `sync_data.sh`).

## Decision tree

| Goal | Tool |
|------|------|
| Deploy **code** (image rebuild) | GitHub **Deploy** workflow (`run_update=true` optional) |
| Scrape **new reviews** now | `./scripts/server.sh prod-update` |
| Hourly scrape | `./scripts/server.sh install-cron` or automatic on **Deploy** workflow |
| Long **artist-image** batch | `./scripts/server.sh start-artist-image-batch` or GitHub **Artist image batch** |
| **MusicBrainz** metadata refresh | `./scripts/server.sh start-metadata-refresh` or GitHub **Metadata refresh** |
| Copy **data/** locally | `./sync_data.sh pull` |
| Read-only check | `./scripts/server.sh status` |

**Do not** `scp`/`rsync` application source to the server except emergencies — use git + Deploy workflow.

## Safety rules

1. **Never** `./sync_data.sh push` while `music-review-artist-image-batch` is running (overwrites server cache).
2. **Never** commit `.env`, `.env.server`, or `data/`.
3. Production update uses `docker compose --profile jobs run --rm music-review-update` (not plain `docker compose run` without `jobs` profile).
4. Wikimedia downloads need `USER_AGENT_*` in server `.env` and `compose.yml` for job containers.
5. After ad-hoc server fixes, **commit** equivalent changes to the repo and deploy via GitHub.

## Key paths on the server

| Path | Purpose |
|------|---------|
| `data/reviews.jsonl` | Scraped reviews; check max `id` field |
| `data/artist_images/` | Local JPG thumbnails (`{mbid}.jpg` or `name:{artist}.jpg`) |
| `data/artist_images.jsonl` | Image cache metadata |
| `logs/hourly-update.log` | Production update log |
| `data/.production_update.lock` | Lock while hourly update runs |

## Containers

| Name | Role |
|------|------|
| `music-review` | FastAPI (always on, port 8000) |
| `music-review-frontend` | React static site via nginx (always on) |
| `music-review-caddy` | HTTPS reverse proxy for plattenradar.de |
| `music-review-artist-image-batch` | Detached batch job (may be absent) |
| `music-review-metadata-refresh` | Detached metadata job (may be absent) |

`music-review-update` is a **one-shot** compose service (not always running).

## Common diagnostics

```bash
./scripts/server.sh status
./scripts/server.sh logs update 80
./scripts/server.sh exec 'docker ps -a --filter name=music-review'
./scripts/server.sh compose --profile jobs ps -a
```

Max review id on server should track [plattentests.de](https://www.plattentests.de/) (`rezi.php?show=ID`). Cron is defined in `deploy/production.crontab` and reinstalled on every **Deploy** workflow run. If data is stale, run `prod-update` and verify `install-cron` / deploy succeeded.

## Write commands (agent may run when user asks)

```bash
./scripts/server.sh prod-update
./scripts/server.sh install-cron
./scripts/server.sh start-artist-image-batch
./scripts/server.sh start-metadata-refresh
./scripts/server.sh start-metadata-refresh overwrite
```

## Codex Cloud / no local SSH key

Use GitHub Actions instead of `server.sh`:

```bash
gh workflow run Deploy --field branch=main --field run_update=true
gh workflow run "Artist image batch"
gh workflow run "Metadata refresh"
```

Leave a note that production verification still requires a machine with SSH or a successful workflow run.
