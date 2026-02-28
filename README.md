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

Many reviews in `metadata.jsonl` have empty genres because MusicBrainz has no tags for that album. **metadata_imputed.jsonl** is a copy of `metadata.jsonl` where those missing genres are filled in from artist profiles.

**How it works:**

1. The tool builds an artist profile from all *other* albums by that artist in `metadata.jsonl` (e.g. “Artist X has 5 albums with genres indie_rock, post_rock; those are this artist’s main genres”).
2. For each metadata entry with empty genres, it looks up the artist profile and uses that artist’s main genres.
3. Imputed entries get a flag `genres_inferred_from_artist: true` so you can see which genres came from MusicBrainz vs which were inferred.

**What it does *not* use:** plattentests.de references, similar artists, or any cross-artist logic. It only reuses genres from other albums by the *same* artist.

**How to create it:**

```bash
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --metadata data/metadata.jsonl \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl
```

You can omit `--artist-profiles-output` if you only want the imputed metadata.

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
```

## Updating data

Refresh each data file with the most current data:

```bash
# 1. Update reviews.jsonl – scrape new reviews (append to existing)
#    Replace MAX_ID with the current highest review ID on plattentests.de
hatch run python -m music_review.pipeline.scraper.cli -v resume --max-id MAX_ID

# 2. Update metadata.jsonl – fetch MusicBrainz metadata for (new) reviews
#    Appends new entries by default. Add --update to refresh existing; --overwrite to start fresh.
hatch run python -m music_review.pipeline.enrichment.fetch_metadata

# 3. Update artist_genres.json – build artist genre profiles from metadata
hatch run python -m music_review.pipeline.enrichment.artist_genres \
  --metadata data/metadata.jsonl \
  --artist-profiles-output data/artist_genres.json \
  --imputed-metadata-output data/metadata_imputed.jsonl
```

## Pre-commit hooks

```bash
hatch run pre-commit install
hatch run pre-commit run --all-files
```
