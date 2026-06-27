# AGENTS.md

## Cursor Cloud specific instructions

### Workflow instructions

- Always include type hints.
- Provide readable, understandable, concise, non-technical (if possible) docstrings.
- **Logging**: Write adequate logs so that progress can be evaluated when running pipelines or CLI tools. Use appropriate levels: **INFO** for normal progress (start, steps, completion), **WARN** for recoverable issues (e.g. fallbacks, retries), **DEBUG** for detailed diagnostics. In CLI tools, support a verbose/DEBUG option (e.g. `-v` / `--verbose`) where useful.
- **Testing**: Mirror the package under `tests/music_review/` — source `src/music_review/foo.py` or `src/music_review/pkg/foo.py` maps to `tests/music_review/test_foo.py` or `tests/music_review/pkg/test_foo.py` (always `test_<module>.py`). Code outside the package (e.g. `pages/page_helpers.py`) lives under `tests/pages/test_page_helpers.py`. Prefer tests that are readable and serve as documentation; use mocks only when necessary (e.g. network or external APIs).
- **Lint workflow**:
  - Run `hatch run lint:fix` regularly while implementing changes.
  - After each coding step, run `hatch run lint:all`.
  - After auto-fixes, continue manually until lint errors are resolved for touched code.
  - Use `#noqa` only in rare, justified cases where the lint finding is not meaningful for the code and there is a strong reason to keep the code unchanged.
  - Prioritize refactoring any "too many local variables per function" findings first.
  - Prefer small, single-responsibility functions that are easy to test.

### Project overview

Music Review is a Python 3.12+ CLI-based data pipeline that scrapes album reviews from plattentests.de, enriches them with MusicBrainz metadata, builds an artist reference graph with communities, and powers a Streamlit dashboard for recommendations and playlists.

### Tooling

- **Build/env manager**: [Hatch](https://hatch.pypa.io/) with `hatchling` build backend
- **Package installer**: [uv](https://docs.astral.sh/uv/) (configured via `hatch config set installer uv`)
- **Linting**: ruff + mypy, orchestrated through hatch environments
- **Testing**: pytest + pytest-cov, orchestrated through hatch environments
- **Pre-commit**: ruff and mypy hooks via `.pre-commit-config.yaml`

### Codex Cloud / mobile workflow

- The GitHub repository is the handoff point for work from mobile or Codex Cloud.
- Cloud work must not assume that private local files under `data/` exist.
- Prefer mocked data, small fixtures, and API/service tests for cloud tasks.
- Run `hatch run lint:all` and `hatch run test:run` before handing back code.
- For changes that need the full review corpus, MusicBrainz calls, Streamlit
  visual checks, or production data updates, leave a clear note that local or
  production verification is still required.
- See `docs/codex-cloud-workflow.md` for the detailed workflow.

### Key commands

| Task | Command |
|------|---------|
| Show all lint + type errors | `hatch run lint:all` |
| Auto-fix ruff errors + reformat | `hatch run lint:fix` |
| Run tests | `hatch run test:run` |
| Run tests with coverage | `hatch run test:cov` |
| Run individual tools | `hatch run lint:check`, `hatch run lint:format`, `hatch run lint:typing` |
| Run scraper | `hatch run python -m music_review.pipeline.scraper.cli -v run --start-id 1 --end-id 10` |
| Update full DB + graph + affinities + DQ | `hatch run update-db` — rebuilds reference graph; **incremental** community IDs from `community_memberships.jsonl` (stable `C00x` + genre labels); `-- --recluster-communities` for full Louvain (then rerun `community-genre-labels`); `album_community_affinities.jsonl` (res 10); after the run writes `data/pipeline_health_report.json` unless `-- --skip-dq`; `-- --dq-strict` fails on warnings; `-- --dq-output PATH` |
| Data-quality report (manual) | `hatch run dq-report` — optional `--expect-graph-artifacts`, `--strict`, `--reviews`, `--metadata-imputed`, `--output` |
| Same as update-db | `hatch run full-data-update` (alias) |
| Artist reference graph | `hatch run graph-build` — GraphML from `data/reviews.jsonl`; add `--export-communities 10` (+ `--export-album-affinities`) for communities; default `--communities-mode incremental` (stable IDs), `--communities-mode louvain` to recluster |
| Community LLM labels | `hatch run community-genre-labels` — `--only-missing` merges with existing JSON and only labels new `community_id` values |
| Streamlit dashboard | `hatch run dashboard` (browse reviews by artist/album) |
| FastAPI (Plattenradar v1) | `hatch run api` |
| Artist image spike CLI | `hatch run artist-image-cli --mbid MBID --artist-name "Name" -v` |
| React frontend dev server | `hatch run frontend` (after `hatch run frontend-install`) |
| Frontend unit tests | `hatch run frontend-test` |
| Frontend UI screenshots | `hatch run frontend-screenshot` (after `hatch run frontend-playwright-install`) |
| Install pre-commit hooks | `hatch run pre-commit install` |

### Streamlit UI (German copy)

User-visible German text in `pages/` and `streamlit_app.py` uses standard orthography (**ä, ö, ü**, **ß**), not ASCII substitutes like `ae`/`oe`/`ue` for those sounds. See `.cursor/rules/german-umlauts-frontend.mdc`.

### Gotchas

- `musicbrainz_client.py` uses `requests` (via `requests.get`). This is now explicitly listed in `pyproject.toml` dependencies.
- `data/moods.py` contains mood constants but is currently unused by the pipeline.
- Set `MUSIC_REVIEW_PROJECT_ROOT` to override the project root. Data paths like `data/reviews.jsonl` are resolved against this (or cwd) so commands work regardless of where you run them from.
- **Python version**: Project is pinned to `>=3.12,<3.14`.
- `OPENAI_API_KEY` is used for community genre labeling during `update-db` (when the graph step runs), not for embeddings.
- MusicBrainz API is rate-limited to ~1 req/s; the client handles this internally.
- The scraper rate-limits to ~2.5 req/s against plattentests.de by default.
- Scraped data is stored in `data/reviews.jsonl` (gitignored). The `data/` directory is auto-created on first scrape.
- `hatch run lint:all` runs ruff check, ruff format --check, and mypy in sequence — all three run even if earlier ones fail, and the exit code reflects any failure.
- Pre-existing mypy errors exist in `parser.py` (BeautifulSoup typing). These are not regressions.
- `update-db` runs, in order: scraper → fetch_metadata → artist_genres → reference_imputation. The last step imputes missing genres from plattentests.de “Referenzen” (first N reference artists with profiles in artist_genres.json) and overwrites `metadata_imputed.jsonl`.

### TODO handling (recommended)
- If you throw me a TODO idea in chat, I will record it in `TODOs.md` in this repo and keep its status up to date there (e.g. open vs done).
- I will keep each TODO stable via an explicit `id:` label inside `TODOs.md` so future updates are unambiguous.
