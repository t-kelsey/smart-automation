# smart-automation

Automated extraction and standardisation of drilling data for a global geodatabase — a hackathon project for the Herrenknecht AG challenge ([Hackathon Portal](https://hackathon.badencampus.de/en/challenges/66f8c41f-b62a-4a84-a356-79546bc9c68b)).

> **Research project, not production software.** This was built during a hackathon. There is **no authentication or authorisation whatsoever**: everyone who can reach the API can read, create and delete data, including the source documents. Do not expose it to the internet, do not run it in production and do not load confidential documents into an instance you do not control. Uploaded pages are possibly to an external LLM (OpenRouter, Claude) depending on the configuration.

## What it does

Legacy borehole logs (scanned or digital PDFs, multilingual, many layouts) are turned into structured, searchable data:

1. **Upload** a borehole report in the web app and choose the model and effort per pipeline step.
2. **Extract**: the pipeline finds the real borehole log pages, splits the report into one PDF per borehole, extracts depth intervals, lithology, stratigraphy and metadata (location, date, elevation) in the original wording, and translates and normalises it to English and to the DIN 4023 terms.
3. **Georeference**: coordinates in local systems (e.g. Gauss-Krüger) are reprojected to WGS84 in PostGIS.
4. **Store** boreholes, layers and the source document in a central PostGIS database.
5. **Search and explore** on an interactive world map, with a query language (name, place, date) and autocompletion, and view each borehole as a DIN 4023 profile column next to its source document.

Every pipeline run is tracked per stage (status, model, tokens, cost) and visible in the web app. A whole run or a single failed extract/transform job can be retried. Boreholes generated for demos are marked `metadata.source = "mock"`.

## Production setup

Everything runs with Docker Compose (`db`, `api`, `web`, `pipeline`). Keep in mind the warning above: put it behind a trusted network or a reverse proxy with authentication.

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD and SECRET_KEY_BASE (openssl rand -base64 48),
# and add ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN for the pipeline,
# or set BEM_AI=openrouter and OPENROUTER_API_KEY to use OpenRouter instead of the claude CLI
docker compose up --build
# open http://localhost:3001
```

- **AI backend:** `BEM_AI=claude_cli` (default, uses `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`) or `BEM_AI=openrouter` (uses `OPENROUTER_API_KEY`, optionally `BEM_OPENROUTER_MODEL` to force one model).
- **Without LLM credentials** the stack still starts; uploads are stored, but extraction runs fail. To see the map and search with data, set `SEED_MOCK_DATA=true` (loads 10 example boreholes plus `MOCK_BOREHOLES` generated ones).
- **Ports** (`.env`): web `WEB_PORT` (3001), API `API_PORT` (4001), pipeline `BEM_PORT` (8000), Postgres 5432. Only the web port needs to be reachable by users; remove the other `ports:` entries from `docker-compose.yml` if you do not need them.
- **Data** lives in the Docker volumes `db_data` (database) and `document_storage` (source documents). `docker compose down -v` deletes both.
- The pipeline queue is in memory: restarting the `pipeline` container loses queued runs.

## Development setup

Prerequisites: Docker, Elixir/Erlang, Node.js ≥ 22.13 with pnpm, and for the pipeline [uv](https://docs.astral.sh/uv/), poppler and either the Claude Code CLI or an OpenRouter API key.

```bash
docker compose up -d db      # PostGIS on localhost:5432
cd api && mix setup && mix phx.server   # API on :4000, seeds example + mock boreholes
cd web && pnpm install && pnpm dev      # UI on :5173, proxies /api to :4000
cd bem && uv sync && uv run python -m pipeline.server   # optional, pipeline on :8000
```

Each part has its own setup details: [api](api/README.md#development-setup), [bem](bem/README.md#development-setup), [web](web/README.md#development-setup).

## Documentation

Read the readme of each component: [api](api/README.md), [bem](bem/README.md), [web](web/README.md) for detailed setup and usage instructions.

See [docs/](docs/) for detailed documentation on architecture, API reference, and design decisions.

### Architecture

```mermaid
flowchart LR
    user([Browser]) --> web
    web["web<br/>SvelteKit UI"] -->|/api| api
    api["api<br/>Phoenix JSON API"] --> db[("PostgreSQL + PostGIS")]
    api -->|"POST /execute, /runs/:id/retry"| bem
    bem["bem<br/>Python pipeline"] -->|"boreholes, stages, reports"| api
    bem <--> llm{{"Claude (claude CLI)<br/>or OpenRouter"}}
```

| Part           | Role                                                                                           | Docs                           |
| -------------- | ---------------------------------------------------------------------------------------------- | ------------------------------ |
| [`api/`](api/) | Owns the data model, georeferencing, search and document storage; exposes the REST API         | [api/README.md](api/README.md) |
| [`bem/`](bem/) | Four-stage LLM pipeline (filter → split → extract → transform) that turns a PDF into boreholes | [bem/README.md](bem/README.md) |
| [`web/`](web/) | Map, search, borehole profile, upload and pipeline monitoring                                  | [web/README.md](web/README.md) |

More detail: [docs/architecture.md](docs/architecture.md) (flows), [docs/api-reference.md](docs/api-reference.md) (endpoints), [docs/adr/](docs/adr/) (decisions).

## Licence

Proprietary, all rights reserved (see [LICENSE](LICENSE) and [ADR-0041](docs/adr/0041-proprietary-all-rights-reserved-licence.md)). The data in `data/` and all dependencies are owned by third parties and are not covered.
