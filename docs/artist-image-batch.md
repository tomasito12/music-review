# Artist image batch prefetch

Offline pipeline for resolving artist photos into `data/artist_images.jsonl` and optional `data/artist_images/*.jpg` files.

## Why

The Plattenradar API should serve cached images only in production (`ARTIST_IMAGE_RESOLVE_ON_DEMAND=false`). The batch job runs external lookups overnight with strict confidence scoring so page loads stay fast and wrong images are rejected.

## Commands

```bash
# Revalidate existing cache entries with current rules
hatch run artist-image-batch --revalidate --report data/artist_image_revalidate_report.json

# Prefetch missing images (all artists, or use --limit N for a slice)
ARTIST_IMAGE_DOWNLOAD=true hatch run artist-image-batch --missing-only --all -v

# Name-only queue only (stricter confidence threshold)
hatch run artist-image-batch --queue name --missing-only --all -v

# Force re-resolve a slice
hatch run artist-image-batch --force --limit 25 -v
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ARTIST_IMAGE_RESOLVE_ON_DEMAND` | `true` | Set `false` in production so API reads cache only |
| `ARTIST_IMAGE_DOWNLOAD` | `false` | Set `true` to store JPG thumbnails under `data/artist_images/` |
| `ARTIST_IMAGE_MIN_CONFIDENCE_MBID` | `70` | Minimum score for MBID-backed matches |
| `ARTIST_IMAGE_MIN_CONFIDENCE_NAME` | `85` | Minimum score for name-only matches |
| `ARTIST_IMAGE_MIN_CONFIDENCE_MEMBER` | `90` | Minimum score for band-member fallback photos |
| `ARTIST_IMAGE_CACHE_TTL_DAYS` | `30` | Negative cache TTL |

## GitHub Actions (production server)

Use the **Artist image batch** workflow (`workflow_dispatch`) to pull the selected
branch on the server and start a **detached** Docker job. The GitHub workflow
returns as soon as the container has started; it does not wait for the batch to
finish (the job may run for days).

Requires the same deploy secrets as the `Deploy` workflow (`DEPLOY_HOST`,
`DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`, optional `DEPLOY_PORT`).

On the server, monitor progress with:

```bash
docker logs -f music-review-artist-image-batch
```

## Rollout

1. Run `--revalidate` once after upgrading validation rules.
2. Run overnight prefetch with `--download --all --missing-only`.
3. Deploy API with `ARTIST_IMAGE_RESOLVE_ON_DEMAND=false`.
4. Monitor the JSON `--report` counters (`rejected_low_confidence`, `resolved_ok`).

## Scheduling

See `deploy/hourly-update.cron.example` or Docker Compose profile `jobs`:

```bash
docker compose --profile jobs run --rm music-review-artist-images
```
