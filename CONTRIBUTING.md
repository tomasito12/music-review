# Contributing

Thank you for your interest in contributing. This project is a Python data
pipeline and web stack for album reviews from [plattentests.de](https://www.plattentests.de),
MusicBrainz enrichment, community-based recommendations, a Streamlit dashboard,
and the Plattenradar React frontend with a FastAPI backend.

## Before you start

- Read the [README](README.md) for setup and pipeline overview.
- For cloud or mobile workflows, see [docs/codex-cloud-workflow.md](docs/codex-cloud-workflow.md).
- For agent-oriented conventions, see [AGENTS.md](AGENTS.md).

## Development setup

Requirements:

- Python **3.12** or **3.13** (`>=3.12,<3.14`)
- [Hatch](https://hatch.pypa.io/) and [uv](https://docs.astral.sh/uv/)
- Node.js **22.12+** and pnpm (for frontend work)

```bash
pip install hatch uv
hatch config set installer uv
hatch run lint:all
hatch run test:run
```

Optional but recommended:

```bash
hatch run pre-commit install
```

For frontend changes:

```bash
corepack enable
hatch run frontend-install
hatch run frontend-test
```

## How to contribute

1. **Open an issue** (or comment on an existing one) to describe the bug,
   improvement, or feature before large changes.
2. **Fork the repository** and create a branch from `main`.
- **Keep changes focused.** Prefer small pull requests that are easy to review.
3. **Follow project conventions:**
   - Python identifiers, docstrings, comments, and logs: **English**
   - User-visible UI copy in Streamlit pages: **German** with correct umlauts
   - Type hints on new Python code
   - Tests under `tests/` mirroring `src/music_review/` layout
4. **Run checks locally** before opening or updating a pull request:

```bash
hatch run lint:fix
hatch run lint:all
hatch run test:run
```

For frontend-only changes, also run:

```bash
hatch run frontend-test
```

If you change React UI that affects visual regression tests, see the CI note in
the pull request template and [docs/codex-cloud-workflow.md](docs/codex-cloud-workflow.md).

5. **Open a pull request** against `main` with a clear description and the
   checklist from the PR template filled in.

## Coding guidelines

### Python

- Use **ruff** and **mypy** via `hatch run lint:all`.
- Prefer small, single-responsibility functions.
- Add tests for non-trivial behavior; mock network and external APIs.
- Use `# noqa` only when justified and rare.
- Log pipeline and CLI progress at appropriate levels (`INFO`, `WARN`, `DEBUG`).

### Frontend

- TypeScript in `frontend/src/`
- Unit tests with Vitest (`hatch run frontend-test`)
- Visual regression references live under `frontend/tests/visual/reference/`

### Data and secrets

- Do **not** commit files under `data/` (gitignored corpus and artifacts).
- Do **not** commit `.env` or API keys (`OPENAI_API_KEY`, deploy credentials).
- Cloud contributors should use fixtures and mocks; full corpus validation is
  a local or production step.

## Pull request expectations

CI runs on every pull request:

- Python lint, format check, and mypy
- Python tests
- Frontend unit tests
- Visual regression (when applicable)
- Docker build smoke test

Address failing checks before merge. If a check cannot pass in your environment
(for example, full-data pipeline runs), explain that in the PR and note what
was verified locally.

## Reporting bugs and suggesting features

Use the GitHub issue templates under `.github/ISSUE_TEMPLATE/`. Include steps to
reproduce, expected vs. actual behavior, and relevant logs or screenshots.

For security issues, do **not** open a public issue. See [SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please be
respectful and constructive in issues, reviews, and discussions.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE), consistent with the project metadata in `pyproject.toml`.
