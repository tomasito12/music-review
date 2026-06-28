# Artist image batch prefetch

Offline pipeline for resolving artist photos into `data/artist_images.jsonl` and optional `data/artist_images/*.jpg` files.

## Why

The Plattenradar API serves artist photos only when a JPG exists under
`data/artist_images/`. Remote Wikimedia URLs in `artist_images.jsonl` alone are not
enough for Aktuell/Entdecken. The batch job runs external lookups offline with strict
confidence scoring so page loads stay fast and wrong images are rejected.

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
| `ARTIST_IMAGE_RESOLVE_ON_DEMAND` | `false` | When `true`, non-API callers may still resolve externally; Plattenradar API endpoints always use cache-only reads |
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

## UI visibility requirement

A photo appears in Aktuell or Entdecken only when **both** are true:

1. `data/artist_images.jsonl` has an `ok` entry for the artist lookup key (MBID or `name:…`).
2. A matching JPG exists under `data/artist_images/` (for example `{mbid}.jpg`).

An `ok` JSONL row without a local JPG still yields `image: null` from
`POST /v1/artists/images`. That is expected while the batch job is still downloading
files.

After deploying or refreshing the cache, hard-reload the frontend if thumbnails stay
empty: the in-memory artist-image session cache can keep earlier `null` results.

## Verification

Sample local readiness for a few artists (JSONL + JPG + API mapping):

```bash
# Cache samples from data/artist_images.jsonl
hatch run artist-image-verify --limit 5 -v

# Sample artists from running API recommendations (also hits POST /v1/artists/images)
hatch run artist-image-verify --from-api --limit 5 -v

# One explicit lookup key
hatch run artist-image-verify --lookup-key "{MBID}" --artist-name "Artist Name" -v
```

Manual spot check for a known MBID:

```bash
ls data/artist_images/{MBID}.jpg
rg '"artist_mbid": "{MBID}"' data/artist_images.jsonl
curl -s -X POST http://localhost:8000/v1/artists/images \
  -H 'Content-Type: application/json' \
  -d '{"artists":[{"artist_mbid":"{MBID}","artist_name":"..."}]}'
curl -I http://localhost:8000/v1/artists/{MBID}/image/file
```

## Rollout

1. Run `--revalidate` once after upgrading validation rules.
2. Run overnight prefetch with `--download --all --missing-only`.
3. Deploy API with `ARTIST_IMAGE_RESOLVE_ON_DEMAND=false`.
4. Monitor the JSON `--report` counters (`rejected_low_confidence`, `resolved_ok`).

## Scheduling

The hourly production update (`music-review-update` / `hatch run prod-update`) prefetches
artist images for **newly scraped reviews only** after metadata enrichment. Use the
overnight batch below for a full backfill of missing images.

See `deploy/hourly-update.cron.example` or Docker Compose profile `jobs`:

```bash
docker compose --profile jobs run --rm music-review-artist-images
```
