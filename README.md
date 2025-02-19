# standard_pipelines

This is our monolithic repo that handles all applications for clients. It was named this way because it was anticipated to mostly be data pipelineing tools, but as the repo has grown, the scope has changed. It may be changed soon because of this.

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
- `uv run flask db upgrade`
- `uv run flask init-flows`
- `uv flask create-default-admin`
- `uv run flask run`
