# standard_pipelines

This is our monolithic repo that handles all applications for clients. We may be changing the name for this soon.

## Setup
- Clone Repo
- Install Docker
- `sudo usermod -aG docker $USER`
- `docker compose -f docker-compose-dev.yaml up`

- Install uv
  - https://docs.astral.sh/uv/getting-started/installation/
  - `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - restart your shell
- `uv sync`
- `uv run flask init-flows`
- `uv flask create-default-admin`
- `uv run flask run`
