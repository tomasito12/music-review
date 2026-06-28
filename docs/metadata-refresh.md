# Metadata refresh (MusicBrainz)

Offline pipeline to re-fetch album metadata from MusicBrainz, rebuild artist genre profiles, and refresh imputed metadata used by the API.

## Why

MusicBrainz lookups can assign the wrong release group or artist MBID. After fixes to validation and matching logic, run a full refresh so `data/metadata.jsonl` and downstream files are rebuilt with the current rules.

## What runs

The detached job runs three steps in order:

1. `fetch_metadata --update` (or `--overwrite`) — re-query MusicBrainz for every review
2. `artist_genres` — rebuild `data/artist_genres.json` and `data/metadata_imputed.jsonl`
3. `reference_imputation` — apply plattentests.de reference-based genre imputation

MusicBrainz is rate-limited to about one request per second, so a full corpus refresh can take days.

## Commands (local)

```bash
# Re-fetch metadata for all reviews (keeps the JSONL file, updates every review id)
hatch run python -m music_review.pipeline.enrichment.fetch_metadata --update

# Wipe metadata.jsonl and rebuild from scratch
hatch run python -m music_review.pipeline.enrichment.fetch_metadata --overwrite

# Rebuild imputed metadata after fetch_metadata
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl
hatch run python -m music_review.pipeline.enrichment.reference_imputation
```

## GitHub Actions (production server)

All long-running jobs use the **`production`** GitHub environment (repository
`Settings -> Environments -> production`) with deploy secrets from
`deploy/README.md`.

### MusicBrainz metadata refresh (recommended after matching fixes)

Use the **Metadata refresh** workflow when you want to re-run
`fetch_metadata --update` for every review (what you started locally with
`--update`). The workflow pulls the selected branch on the server and starts a
**detached** Docker container. It returns as soon as the container has started;
it does not wait for the refresh to finish.

**GitHub UI:** Actions -> **Metadata refresh** -> Run workflow

**CLI:**

```bash
gh workflow run "Metadata refresh" --field branch=main --field mode=update
```

| Input | Default | Meaning |
|-------|---------|---------|
| `branch` | `main` | Git branch to deploy before starting |
| `mode` | `update` | `update` re-fetches every review; `overwrite` deletes and rebuilds `metadata.jsonl` |

Monitor on the server:

```bash
docker logs -f music-review-metadata-refresh
# or locally:
./scripts/server.sh logs metadata
```

### Full database update (scrape + graph + optional metadata refresh)

Use the **Update database** workflow for `hatch run update-db` on the server
(scraper, metadata, imputation, graph, DQ). Enable `metadata_update=true` to
include a full MusicBrainz re-fetch in that run.

```bash
gh workflow run "Update database" --field branch=main
gh workflow run "Update database" \
  --field branch=main \
  --field metadata_update=true \
  --field skip_reviews=true
```

Monitor: `docker logs -f music-review-update-db` or `./scripts/server.sh logs update-db`

### Hourly incremental update

The **Deploy** workflow with `run_update=true` runs the hourly production job
(scrape new reviews + incremental metadata only). Cron on the server does the
same every hour.

Or start manually:

```bash
./scripts/start_metadata_refresh.sh
METADATA_REFRESH_MODE=overwrite ./scripts/start_metadata_refresh.sh
```

State is written to `data/.metadata_refresh.state` when the job starts.

## Environment

Uses the same `.env` and `data/` volume mount as other job containers (`MUSIC_REVIEW_PROJECT_ROOT=/app`). No extra variables are required beyond optional `METADATA_REFRESH_MODE` and `METADATA_REFRESH_CONTAINER`.
