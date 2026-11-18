# api

Phoenix JSON API and system of record of the geodatabase.

## Why it exists

The web app and the extraction pipeline both need one place that owns the borehole data model. The API stores boreholes, layers, documents and pipeline runs, georeferences coordinates, serves map, search and detail queries, hands uploaded documents to the pipeline and receives its results. Because the API owns the data model, the other parts adapt to it ([ADR-0001](../docs/adr/0001-borehole-data-model-and-api-contract.md)). Endpoints: [docs/api-reference.md](../docs/api-reference.md).

## Development setup

Prerequisites: Elixir/Erlang (see `mix.exs`) and PostGIS, e.g. `docker compose up -d db` from the repo root (user/password `postgres`).

```bash
cd api
mix setup          # deps, create/migrate DB, seed 10 examples + 1000 generated boreholes
mix phx.server     # http://localhost:4000

# Optional checks
mix test           # run the tests
mix precommit      # warnings-as-errors, format, tests — run before finishing a change
```

- More or less mock data: `MOCK_BOREHOLES=1000000 mix run priv/repo/seeds.exs` (max 1,000,000) or `mix boreholes.mock --count 5000`. Generated rows carry `metadata.source = "mock"`; re-running replaces them and never touches real data.
- Section test data: `mix boreholes.section_mock` (in Docker: `bin/api eval "Api.Release.section_mock()"`) inserts ten boreholes `SL-01`…`SL-10` along a 1 km line in Stuttgart-Feuerbach (9.1340, 48.8050 → 9.1475, 48.8030) for the map's section view; they carry `metadata.source = "section-mock"` and are replaced on re-run.
- Existing documents: put files in `priv/uploads/` and run `mix documents.backfill`; they are moved to `priv/storage/` (both gitignored, documents are confidential).
- Duplicate upload detection needs `documents.sha256`; fill it for documents stored before it existed (or added by `mix documents.backfill`) with `mix documents.sha256`, in Docker `docker compose exec api bin/api eval "Api.Release.backfill_sha256()"`.
- `PIPELINE_URL` (default off in dev) is where runs are sent, e.g. `http://localhost:8000/execute`.
- Rules for working in this code: [AGENTS.md](AGENTS.md).

## Technology

| Choice                          | Why                                                                                                                                                                                                               |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Elixir + Phoenix 1.8**        | A small, fast JSON API with little boilerplate; the BEAM handles concurrent uploads and background calls to the pipeline well.                                                                                    |
| **Ecto**                        | Explicit schemas and changesets validate the borehole data model at the boundary; dynamic queries power the search.                                                                                               |
| **PostgreSQL + PostGIS**        | Geometry columns, spatial indexes and `ST_Transform` reproject coordinates from any EPSG code to WGS84 inside the database ([ADR-0001](../docs/adr/0001-borehole-data-model-and-api-contract.md)).                  |
| **`pg_trgm`**                   | Typo-tolerant search and autocompletion with GIN indexes, no separate search engine ([ADR-0003](../docs/adr/0003-search-query-and-autocompletion.md)). |
| **Bandit, Req**                 | Default Phoenix web server; Req is the HTTP client for calling the pipeline.                                                                                                                                      |
| **Filesystem document storage** | Source documents stay in a volume under our control instead of the database ([ADR-0002](../docs/adr/0002-document-intake-and-pipeline-runs.md)).                                                               |

**Limitations:** no authentication, and `elevation_m` must currently be ≥ 0, so boreholes below sea level are rejected.

## Architecture

A conventional Phoenix layout with a thin web layer on top of one Ecto context:

```
Router → Controller (+ params, JSON view) → Api.Boreholes context → Ecto schemas → PostgreSQL/PostGIS
                                          → Api.Pipeline          → bem pipeline (HTTP)
```

- **Web layer** (`lib/api_web/`): the router exposes everything under `/api`. Controllers validate and cast request params, call the context and render with a `*_json.ex` view, so the response shape is defined in one place. Errors go through a shared `FallbackController`.
- **Context** (`lib/api/boreholes.ex`): the only module the controllers use for data. It holds the queries (bounding-box filter for the map, paging, search ranking) and the writes, so business rules do not leak into controllers.
- **Review** (`lib/api/boreholes/review.ex`, `checks.ex`): human edits with their history, revert, flags and verification, and the plausibility checks that keep the rule flags in sync after every change (ADR-0006).
- **Schemas** (`lib/api/boreholes/`): `Borehole` (with a PostGIS point), `BoreholeLayer`, `FieldFlag`, `FieldEdit`, `Document`, `PipelineRun`, `ExecStage` and `Report`, with changesets that validate data at the boundary. `SearchQuery` parses the search query language into Ecto conditions that run in Postgres.
- **Pipeline client** (`lib/api/pipeline.ex`): sends a run to the bem service with `Req` can stop it and can ask it to redo one failed extract/transform/validate job (`POST /api/exec_stages/:id/retry`, which reopens the run). Pipeline progress comes back through the API's own endpoints (`exec_stages`, `reports`, `boreholes`, `pipeline_runs/:id/status`), so bem never touches the database or the document storage directly.
- **Storage:** structured data in PostGIS, source documents as files in `DOCUMENT_STORAGE_DIR`, linked to boreholes through `documents` rows.
- **Releases:** the Docker image runs migrations (and optional seeding) through `Api.Release` before starting the server.
