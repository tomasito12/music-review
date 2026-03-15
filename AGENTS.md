# AGENTS.md

## Cursor Cloud specific instructions

### Workflow instructions

- Always include type hints.
- Provide readable, understandable, concise, non-technical (if possible) docstrings.
- **Logging**: Write adequate logs so that progress can be evaluated when running pipelines or CLI tools. Use appropriate levels: **INFO** for normal progress (start, steps, completion), **WARN** for recoverable issues (e.g. fallbacks, retries), **DEBUG** for detailed diagnostics. In CLI tools, support a verbose/DEBUG option (e.g. `-v` / `--verbose`) where useful.
- **Testing**: Use one test module per source module (e.g. `config.py` → `tests/test_config.py`; `io/jsonl.py` → `tests/io/test_jsonl.py`; `pipeline/scraper/client.py` → `tests/pipeline/scraper/test_client.py`). Prefer tests that are readable and serve as documentation; use mocks only when necessary (e.g. network or external APIs).

### Project overview

Music Review is a Python 3.12+ CLI-based data pipeline that scrapes album reviews from plattentests.de, enriches them with MusicBrainz metadata, and indexes reviews into a ChromaDB vector store using OpenAI embeddings. There is no web framework or Docker setup — everything runs as local CLI commands.

### Tooling

- **Build/env manager**: [Hatch](https://hatch.pypa.io/) with `hatchling` build backend
- **Package installer**: [uv](https://docs.astral.sh/uv/) (configured via `hatch config set installer uv`)
- **Linting**: ruff + mypy, orchestrated through hatch environments
- **Testing**: pytest + pytest-cov, orchestrated through hatch environments
- **Pre-commit**: ruff and mypy hooks via `.pre-commit-config.yaml`

### Key commands

| Task | Command |
|------|---------|
| Show all lint + type errors | `hatch run lint:all` |
| Auto-fix ruff errors + reformat | `hatch run lint:fix` |
| Run tests | `hatch run test:run` |
| Run tests with coverage | `hatch run test:cov` |
| Run individual tools | `hatch run lint:check`, `hatch run lint:format`, `hatch run lint:typing` |
| Run scraper | `hatch run python -m music_review.pipeline.scraper.cli -v run --start-id 1 --end-id 10` |
| Update full DB | `hatch run update-db` (or `-- --max-id MAX_ID` to set an upper bound) |
| Batch embeddings (OpenAI Batch API → Chroma) | `hatch run batch-embed prepare` then `batch-embed submit <batch_id>` etc., or `hatch run batch-embed run` for full pipeline |
| Artist reference graph | `hatch run graph-build` (builds from `data/reviews.jsonl`, writes `data/artist_reference_graph.graphml`) |
| Streamlit dashboard | `hatch run dashboard` (browse reviews by artist/album) |
| Install pre-commit hooks | `hatch run pre-commit install` |

### Gotchas

- `musicbrainz_client.py` uses `requests` (via `requests.get`). This is now explicitly listed in `pyproject.toml` dependencies.
- `data/moods.py` contains mood constants but is currently unused by the pipeline.
- Set `MUSIC_REVIEW_PROJECT_ROOT` to override the project root. Data paths like `data/reviews.jsonl` are resolved against this (or cwd) so commands work regardless of where you run them from.
- **Python version**: ChromaDB (Pydantic v1) does not support Python 3.14+. The project is pinned to `>=3.12,<3.14`. If you see `ConfigError: unable to infer type for attribute "chroma_server_nofile"`, your Hatch env is using 3.14: run `hatch env prune` then `hatch run batch-embed …` so Hatch recreates the env with 3.12 or 3.13.
- The vector store module (`pipeline/retrieval/vector_store.py`) requires the `OPENAI_API_KEY` environment variable. Without it, only scraping and metadata enrichment stages can run. The batch embedding pipeline (`hatch run batch-embed`) uses the same key for upload/create/poll/download and for Chroma.
- MusicBrainz API is rate-limited to ~1 req/s; the client handles this internally.
- The scraper rate-limits to ~2.5 req/s against plattentests.de by default.
- Scraped data is stored in `data/reviews.jsonl` (gitignored). The `data/` directory is auto-created on first scrape.
- `hatch run lint:all` runs ruff check, ruff format --check, and mypy in sequence — all three run even if earlier ones fail, and the exit code reflects any failure.
- Pre-existing mypy errors exist in `parser.py` (BeautifulSoup typing) and `vector_store.py` (ChromaDB type signatures). These are not regressions.
- `update-db` runs, in order: scraper → fetch_metadata → artist_genres → reference_imputation. The last step imputes missing genres from plattentests.de “Referenzen” (first N reference artists with profiles in artist_genres.json) and overwrites `metadata_imputed.jsonl`.
