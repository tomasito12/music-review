# AGENTS.md

## Cursor Cloud specific instructions

### Workflow instructions

- Always include type hints.
- Provide readable, understandable, concise, non-technical (if possible) docstrings.

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
| Run scraper | `hatch run python -m music_review.scraper.cli -v run --start-id 1 --end-id 10` |
| Install pre-commit hooks | `hatch run pre-commit install` |

### Gotchas

- `musicbrainz_client.py` uses `requests` (via `requests.get`). This is now explicitly listed in `pyproject.toml` dependencies.
- `data/moods.py` contains mood constants but is currently unused by the pipeline.
- Set `MUSIC_REVIEW_PROJECT_ROOT` to override the project root (used by vector store paths). Defaults to current working directory.
- The vector store module (`retrieval/vector_store.py`) requires the `OPENAI_API_KEY` environment variable. Without it, only scraping and metadata enrichment stages can run.
- MusicBrainz API is rate-limited to ~1 req/s; the client handles this internally.
- The scraper rate-limits to ~2.5 req/s against plattentests.de by default.
- Scraped data is stored in `data/reviews.jsonl` (gitignored). The `data/` directory is auto-created on first scrape.
- `hatch run lint:all` runs ruff check, ruff format --check, and mypy in sequence — all three run even if earlier ones fail, and the exit code reflects any failure.
- Pre-existing mypy errors exist in `parser.py` (BeautifulSoup typing) and `vector_store.py` (ChromaDB type signatures). These are not regressions.
