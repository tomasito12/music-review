# Deployment

## GitHub Actions secrets

Create these repository secrets under `Settings -> Secrets and variables -> Actions`:

- `DEPLOY_HOST`: server hostname or IP address.
- `DEPLOY_USER`: SSH user on the server.
- `DEPLOY_SSH_KEY`: private SSH key allowed to log in as `DEPLOY_USER`.
- `DEPLOY_PATH`: absolute path to this repository on the server.
- `DEPLOY_PORT`: SSH port. Optional when the server uses port `22`.

Keep production `.env` and `data/` files on the server. The GitHub workflow does
not upload local secrets or data.

## Server prerequisites

- The repository is already cloned at `DEPLOY_PATH`.
- Docker and Docker Compose are installed for `DEPLOY_USER`.
- The server checkout has a production `.env` file.
- `DEPLOY_USER` can run `git fetch`, `docker compose build`, and
  `docker compose up -d`.

## Manual deploy

Open the `Deploy` workflow in GitHub Actions, choose the branch, and run it.
The workflow verifies lint/tests first, then deploys over SSH:

1. Fetch and fast-forward the selected branch on the server.
2. Rebuild the `music-review` image.
3. Restart `music-review` and `caddy`.
4. Optionally run `music-review-update`.
5. Check the local Streamlit health endpoint in the container.
