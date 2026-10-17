# smart-automation

**Challenge**

Automated extraction and standardisation of drilling data for a global geodatabase (By Herrenknecht AG).

[Hackathon Portal](https://hackathon.badencampus.de/en/challenges/66f8c41f-b62a-4a84-a356-79546bc9c68b)

[Herrenknecht fileshare](https://fileshare.herrenknecht.com/download;jsessionid=node0sfhoqch7owhb1ozu1tbebpev151416.node0?0&id=Soq0VEfmJL)
Passwort: siehe email

# Development Setup

## Prerequisites

- Docker (for the local Postgres+PostGIS container)
- Elixir/Erlang (see `api/mix.exs` for the required Elixir version)
- Node.js >= 22.13 (see `web/.nvmrc`; `nvm use` picks it up automatically) + [pnpm](https://pnpm.io/)

## 1. Database (Postgres + PostGIS)

A `docker-compose.yml` is provided at the repo root so nobody needs PostGIS installed locally:

```bash
docker compose up -d   # Starts Postgres+PostGIS on localhost:5432 (user/password: postgres)
```

If you already have a local Postgres running on port 5432 (e.g. via Homebrew), stop it first,
otherwise the app will silently connect to the wrong database:

```bash
brew services stop postgresql@14   # or whichever version you have running
```

## 2. API (`api/`)

```bash
cd api
mix setup           # Installs deps and creates/migrates/seeds the database
mix phx.server       # Starts the dev server on localhost:4000
```

`mix setup` runs `mix ecto.create` + `mix ecto.migrate` for you. If you ever need to run them
individually (e.g. after pulling new migrations), that's `mix ecto.create` and `mix ecto.migrate`.

`mix setup` also applies `priv/repo/seeds.exs`, which inserts 10 hand-written example boreholes
plus 1000 generated ones (`Api.MockData`), so there's something to query right away. Re-running
the seeds replaces the seeded and generated rows instead of duplicating them; real data is kept.

```bash
mix run priv/repo/seeds.exs                        # 10 examples + 1000 generated boreholes
MOCK_BOREHOLES=1000000 mix run priv/repo/seeds.exs # the maximum
mix boreholes.mock --count 5000                    # only replace the generated boreholes
```

Generated boreholes are marked with `metadata.source = "mock"`. Whenever seeds or mock data are
created, `api/priv/repo/assets/borehole_log_example.pdf` is copied into the document storage
directory (`DOCUMENT_STORAGE_DIR`, default `api/priv/storage/`) as `mock_borehole_log_example.pdf`,
and every seeded or generated document — whatever its name — points at that one file, so the
document viewer works for all of them. With `MOCK_BOREHOLES=0` only the 10 hand-written examples
are seeded.

Run `mix precommit` before considering any backend change done — it compiles with
warnings-as-errors, checks for unused deps, formats, and runs the full test suite.

### Loading sample borehole documents

Confidential source documents (PDFs/scans/images) are never committed to git. To get sample data
into the database and queryable via the API:

1. Drop files (or whole folders — subfolders are flattened) into `api/priv/uploads/`. This
   directory is a staging inbox; anything placed there is **not yet** tracked in the database.
2. Run the backfill task from inside `api/`:
   ```bash
   mix documents.backfill
   ```
   For each file found in `priv/uploads/`, this creates a `documents` row and **moves** the file
   into `api/priv/storage/`, renamed to `<document_id><ext>` (e.g. `3fa85f64-....pdf`). After a
   successful run, `priv/uploads/` is empty again and the files live in `priv/storage/`, matched
   to their `documents` row purely by filename.

Both `priv/uploads/` and `priv/storage/` are gitignored (only `.gitkeep` is tracked) — this is
expected, the actual files only ever live on your machine.

## 3. Web (`web/`)

```bash
cd web
pnpm install        # Install web dependencies
pnpm dev            # Start web development server
```

# Production Setup

Prerequisites:
- Docker
- Docker Compose

```bash
# Create environment file
cp .env.example .env

# Edit `.env` to configure your environment variables as needed.
vi .env

# Start application
docker compose up --build

# open localhost:3001 in browser
```

# Licence

Proprietary, all rights reserved (see [LICENSE](LICENSE) and [ADR-0041](docs/adr/0041-proprietary-all-rights-reserved-licence.md)). The data in `data/` and all dependencies are owned by third parties and are not covered.
