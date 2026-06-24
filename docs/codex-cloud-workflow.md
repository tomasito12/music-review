# Codex Cloud Workflow

This project can be worked on from a phone through Codex Cloud as long as the
repository is available on GitHub. In that mode, Codex checks out the GitHub
repository in a cloud environment, works on a branch, and returns changes through
commits or pull requests. The local Mac does not need to be running for those
tasks.

## What Works In The Cloud

- Editing Python source, tests, docs, and frontend code.
- Running the normal verification commands:

```bash
hatch run lint:all
hatch run test:run
```

- Building small API and frontend changes against test fixtures.
- Opening pull requests on GitHub.
- Reviewing CI results from GitHub Actions.

The current CI already runs linting, type checks, tests, and a Docker build smoke
test on GitHub.

## What Needs Local Or Production Data

The real review corpus and generated artifacts live under `data/`, which is
gitignored and not available in Codex Cloud by default. This includes files such
as:

- `data/reviews.jsonl`,
- `data/metadata.jsonl`,
- `data/metadata_imputed.jsonl`,
- `data/album_community_affinities.jsonl`,
- `data/community_memberships.jsonl`,
- `data/plattenradar.db`.

Cloud tasks should therefore not assume that the full dashboard can show real
recommendations unless a task explicitly provides fixture data or a separate data
sync mechanism.

## Recommended Mobile Workflow

1. Start or continue a Codex task from ChatGPT/Codex on mobile.
2. Ask Codex to work against the GitHub repository, not the local Mac workspace.
3. Keep tasks scoped to code, tests, docs, API contracts, and UI structure.
4. Let Codex run `hatch run lint:all` and `hatch run test:run`.
5. Have Codex open a pull request.
6. Review the pull request and GitHub Actions results from mobile.
7. Later, pull the branch locally on the Mac for real-data checks or visual QA.

## Good Cloud Tasks

- Add or refine API endpoints with mocked data tests.
- Build React/Vite frontend structure against mocked or small fixture responses.
- Improve Pydantic models, service boundaries, and docs.
- Add regression tests for existing business logic.
- Update product specs and implementation notes.

## Tasks To Keep Local For Now

- Running the full scraper or full data update against plattentests.de.
- Running MusicBrainz-heavy enrichment jobs.
- Running community genre labeling with `OPENAI_API_KEY`.
- Validating recommendations against the full private corpus.
- Visual checks that depend on the local Streamlit dashboard and full data.

## Secrets

Do not commit secrets or real environment files. Use GitHub repository secrets
for CI/deploy credentials and local `.env` files for development. The project
already ignores `.env` and `data/`.

`OPENAI_API_KEY` is only needed for community genre labeling during data update
work. It is not needed for the normal test suite.
