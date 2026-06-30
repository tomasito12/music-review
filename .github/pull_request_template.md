## Summary

<!-- What changed and why? Link related issues (e.g. Fixes #123). -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Documentation
- [ ] CI / tooling
- [ ] Frontend UI
- [ ] Pipeline / data (requires local or production verification)

## Areas touched

- [ ] Python (`src/music_review/`, `pages/`, scripts)
- [ ] Tests (`tests/`)
- [ ] Frontend (`frontend/`)
- [ ] Docs only
- [ ] GitHub workflows / deployment

## Verification

Commands run locally (check all that apply):

- [ ] `hatch run lint:all`
- [ ] `hatch run test:run`
- [ ] `hatch run frontend-test` (frontend changes)
- [ ] Manual API / Streamlit check
- [ ] Full pipeline or production data check (note below if not run)

<!-- If CI-only or cloud work, say what could not be verified locally. -->

## UI / visual regression

If this changes React UI captured by visual tests:

- [ ] Not applicable
- [ ] Updated reference screenshots locally, or
- [ ] Will run the **Update visual screenshots** workflow after merge

## Notes for reviewers

<!-- Optional: design choices, follow-ups, migration steps. -->

## Checklist

- [ ] Code identifiers, comments, and logs are in English; German only for user-visible Streamlit copy where applicable
- [ ] No secrets, `.env` files, or `data/` artifacts committed
- [ ] New Python code includes type hints; tests added or updated when behavior changed
