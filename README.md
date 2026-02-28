# music-review

Music review scraper and RAG data pipeline.

Scrapes album reviews from [plattentests.de](https://www.plattentests.de),
enriches them with metadata from the [MusicBrainz](https://musicbrainz.org) API,
and indexes the reviews into a [ChromaDB](https://www.trychroma.com) vector store
using OpenAI embeddings for semantic search and retrieval.

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
hatch run python -m music_review.scraper.cli -v run --start-id 1 --end-id 100

# Fetch MusicBrainz metadata for scraped reviews
hatch run python -m music_review.metadata.fetch_metadata

# Build artist genre profiles and impute missing genres
hatch run python -m music_review.metadata.artist_genres \
  --metadata data/metadata_1.jsonl \
  --artist-profiles-output data/artist_profiles.json \
  --imputed-metadata-output data/metadata_imputed.jsonl

# Build the vector store (requires OPENAI_API_KEY)
hatch run python -m music_review.retrieval.vector_store
```

## Pre-commit hooks

```bash
hatch run pre-commit install
hatch run pre-commit run --all-files
```
