# music-review

Music review scraper and RAG data pipeline.

Scrapes album reviews from [plattentests.de](https://www.plattentests.de),
enriches them with metadata from the [MusicBrainz](https://musicbrainz.org) API,
and indexes the reviews into a [ChromaDB](https://www.trychroma.com) vector store
using OpenAI embeddings for semantic search and retrieval.

## How the data files are created

The pipeline builds three data files in sequence; each step uses the output of the previous one.

1. **reviews.jsonl** – Scraped by the CLI from plattentests.de. For each review ID it fetches the HTML page, parses artist, album, text, rating, tracklist, etc. with BeautifulSoup, and writes one JSON object per line.

2. **metadata.jsonl** – Created by `fetch_metadata`. It reads `reviews.jsonl`, looks up each (artist, album) in the MusicBrainz API to get tags and artist info, maps tags to genres via regex rules, and writes one metadata entry per review (review_id, artist, album, genres, artist_mbid, etc.).

3. **artist_genres.json** – Created by `artist_genres`. It reads `metadata.jsonl`, aggregates genres per artist (grouped by MusicBrainz ID or name), computes each artist’s main genres, and writes a JSON map of artist profiles. Optionally it can produce `metadata_imputed.jsonl` (see below).

### Genre imputation (metadata_imputed.jsonl)

Many reviews in `metadata.jsonl` have empty genres because MusicBrainz has no tags for that album. **metadata_imputed.jsonl** is produced in two steps:

**Step 1 – Same-artist imputation** (artist_genres):

1. Build an artist profile from all *other* albums by that artist in `metadata.jsonl`.
2. For each metadata entry with empty genres, use that artist’s main genres from their profile.
3. Imputed entries get `genres_inferred_from_artist: true`.

**Step 2 – Reference imputation** (reference_imputation):

4. For entries that *still* have empty genres, use the review’s “Referenzen” (reference artists) from plattentests.de.
5. Take the first N references (default 3) that match an artist in `artist_genres.json` and have genres; aggregate their genre counts and apply the same main-genre rule.
6. Imputed entries get `genres_inferred_from_references: true` and `reference_artists_used: ["…", "…"]`.

**How to create it:** The full pipeline (including both imputation steps) is run by `hatch run update-db`. To run only imputation:

```bash
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --metadata data/metadata.jsonl \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl

hatch run python -m music_review.pipeline.enrichment.reference_imputation \
  --imputed-metadata data/metadata_imputed.jsonl \
  --reviews data/reviews.jsonl \
  --artist-genres data/artist_genres.json
```

Reference imputation overwrites `metadata_imputed.jsonl` with the result (or use `--output` to write elsewhere).

## Quick start

```bash
# Install hatch (project manager) and uv (fast Python package installer)
pip install hatch uv
hatch config set installer uv

# Run linting
hatch run lint:all          # ruff check + ruff format --check + mypy
hatch run lint:fix          # auto-fix ruff errors and reformat

# Run tests with coverage
hatch run test:cov

# Run the scraper (example: scrape reviews 1–100)
hatch run python -m music_review.pipeline.scraper.cli -v run --start-id 1 --end-id 100

# Fetch MusicBrainz metadata for scraped reviews
hatch run python -m music_review.pipeline.enrichment.fetch_metadata

# Build artist genre profiles and impute missing genres
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --metadata data/metadata_1.jsonl \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl

# Build the vector store (requires OPENAI_API_KEY)
hatch run python -m music_review.pipeline.retrieval.vector_store

# Start the Streamlit dashboard (browse reviews and metadata)
hatch run dashboard
```

## Dashboard

A Streamlit dashboard lets you browse reviews and metadata by artist and album:

```bash
hatch run dashboard
```

Then open the URL shown in the terminal (default: http://localhost:8501). Select an **artist**, then an **album**, to view the full review text plus metadata (rating, labels, release, tracklist, highlights, references) and MusicBrainz data (genres, artist MBID, etc.) when available. Data paths are resolved from the project root, so run from any directory.

## Updating data

### One command (full update)

Updates reviews, metadata, imputation, **reference graph** (`artist_reference_graph.graphml`), **community exports** (`communities_res_10.json`, `community_memberships.jsonl`), **`album_community_affinities.jsonl`**, and **by default** incremental **Chroma chunks** (`music_reviews_chunks_v1`, OpenAI Batch API). Paths resolve relative to the project root (or `MUSIC_REVIEW_PROJECT_ROOT`).

**Stable communities:** `update-db` keeps existing `C00x` IDs from `community_memberships.jsonl` and only assigns **new** artists via the reference graph (so `community_genre_labels_res_10.json` stays valid). The first run on a machine without that file falls back to Louvain once. To **rebuild** clusters from scratch (new IDs — relabel communities afterwards), use `--recluster-communities`.

```bash
# Full pipeline including graph + affinities + chunk Chroma (OPENAI_API_KEY for Chroma)
hatch run update-db

# Skip Chroma only (still rebuilds graph + album_community_affinities)
hatch run update-db -- --skip-chroma

# Skip graph/affinities (faster; keeps existing album_community_affinities.jsonl)
hatch run update-db -- --skip-graph-affinities

# Full Louvain recluster (invalidates community genre labels until you re-run LLM labels)
hatch run update-db -- --recluster-communities

# Also update the legacy whole-review collection (music_reviews)
hatch run update-db -- --chroma-legacy

# Or specify a maximum review ID for the scraper
hatch run update-db -- --max-id MAX_ID
```

`hatch run full-data-update` is the same script; pass through the same flags.

Options: `--verbose`, `--metadata-update`, `--skip-reviews`, `--metadata-min-review-id ID`, `--skip-graph-affinities`, `--recluster-communities`, `--skip-chroma`, `--chroma-legacy`.

**Chroma:** Without `OPENAI_API_KEY`, JSONL steps still run; Chroma is **skipped** with a warning.

**Metadata fetch behaviour:** By default, `fetch_metadata` **skips** any `review_id` that already exists in `metadata.jsonl` and only calls MusicBrainz for **missing** rows. It still **scans** the whole `reviews.jsonl`, so you may see log lines for low ids if those rows are missing from metadata (e.g. gaps or a new output file). **`--metadata-update`** re-fetches **every** review (slow). After a scraper `resume`, if you only want MusicBrainz for **new high ids** and accept not filling old gaps, use e.g. `--metadata-min-review-id 21300` (pick the first id you care about).

### Step by step

Refresh each data file individually:

```bash
# 1. Update reviews.jsonl – scrape new reviews (append to existing)
#    Omit --max-id to auto-stop after 3 consecutive missing IDs
hatch run python -m music_review.pipeline.scraper.cli -v resume

# 2. Update metadata.jsonl – fetch MusicBrainz metadata for (new) reviews
#    Appends new entries by default. Add --update to refresh existing; --overwrite to start fresh.
hatch run python -m music_review.pipeline.enrichment.fetch_metadata

# 3. Update artist_genres.json and metadata_imputed.jsonl (same-artist + reference imputation)
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --metadata data/metadata.jsonl \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl
hatch run python -m music_review.pipeline.enrichment.reference_imputation \
  --imputed-metadata data/metadata_imputed.jsonl --reviews data/reviews.jsonl \
  --artist-genres data/artist_genres.json

# 4. Reference graph + communities (incremental by default when community_memberships.jsonl exists)
hatch run graph-build -- --export-communities 10 --export-album-affinities
# Louvain re-baseline (optional): add --communities-mode louvain

# 5. Community genre labels (OpenAI). After incremental graph updates, reuse labels:
hatch run community-genre-labels -- --only-missing
```

## Pre-commit hooks

```bash
hatch run pre-commit install
hatch run pre-commit run --all-files
```
