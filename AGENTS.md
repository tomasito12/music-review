# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Music Review is a Python 3.12+ CLI-based data pipeline that scrapes album reviews from plattentests.de, enriches them with MusicBrainz metadata, and indexes reviews into a ChromaDB vector store using OpenAI embeddings. There is no web framework or Docker setup — everything runs as local CLI commands.

### Running the application

- **Scraper**: `python3 -m music_review.scraper.cli -v run --start-id 1 --end-id 10`
- **Metadata fetch**: `python3 -m music_review.metadata.fetch_metadata` (requires scraped data in `data/`)
- **Artist genres**: `python3 -m music_review.metadata.artist_genres` (requires metadata)
- **Vector store / RAG**: `python3 -m music_review.retrieval.vector_store` (requires `OPENAI_API_KEY`)

### Lint and test

- **Lint**: `ruff check .` — project has 15 pre-existing lint warnings (import sorting, line length, unused import). These are not introduced by agents.
- **Test**: `python3 -m pytest` — no test files exist in the project currently; pytest exits with code 5 (no tests collected).

### Gotchas

- `musicbrainz_client.py` uses `requests` (via `requests.get`) but `requests` is **not** listed in `pyproject.toml` dependencies. It is available as a transitive dependency (via `kubernetes` pulled by `chromadb`). If ChromaDB is ever removed, `requests` must be added explicitly.
- The ruff config in `pyproject.toml` uses a deprecated top-level `select` key; ruff emits a deprecation warning suggesting `lint.select` instead.
- The vector store module (`retrieval/vector_store.py`) requires the `OPENAI_API_KEY` environment variable to be set for embedding generation. Without it, only the scraping and metadata enrichment stages can run.
- MusicBrainz API is rate-limited to ~1 req/s; the client handles this internally.
- The scraper rate-limits to ~2.5 req/s against plattentests.de by default.
- Scraped data is stored in `data/reviews.jsonl` (gitignored). The `data/` directory is auto-created on first scrape.
