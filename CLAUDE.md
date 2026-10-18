# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Challenge

According to the challenge description on the website the goal and the metric are relevant for the evaluation of the solution. These should always be considered when designing, assessing and implementing a feature.

### Challenge Goal

Develop a system that automatically extracts borehole profiles from PDFs, scans and images, converts them into a standardised format, georeferences them and stores them in a central database that can be searched via an interactive world map.

### Challenge Metric

Success metric: The solution demonstrates reliable extraction, standardisation, georeferencing and storage of borehole profiles. The extracted profiles can be searched in the database and displayed on an interactive world map. Examples can be found in the provided dataset.

## Project

Hackathon project (Herrenknecht challenge): automated extraction and standardisation of drilling/borehole data into a global geodatabase. Research code, not production software: there is no authentication (the READMEs say so). Monorepo with three apps plus docs and data, run together by the root `docker-compose.yml` (`db`, `api`, `web`, `pipeline`):

- `api/` — Phoenix 1.8 JSON API (Elixir, Ecto, PostGIS, Bandit). Owns the data model, georeferencing, search and document storage. Endpoints (boreholes, documents, pipeline_runs, exec_stages, reports) are documented in `docs/api-reference.md`; `mix boreholes.mock --count N` (max 1000000) generates mock data.
- `web/` — SvelteKit 3 / Svelte 5 frontend (TypeScript, Tailwind 4, Skeleton, MapLibre, pnpm): map, search with autocompletion, DIN 4023 borehole profile, upload with pipeline config, pipeline run monitoring and review pages. Some features (document management, sharing, auth) are deliberately left out of scope, see the root README.
- `bem/` — Python pipeline (FastAPI) that runs a 4-stage LLM pipeline (filter → split → extract → transform) over a borehole document (PDF, images and Word are converted to PDF) and posts the result to `POST /api/boreholes`. AI backend is OpenRouter (default) or, for development only, the `claude` CLI (`BEM_AI`). Endpoints: `POST /execute`, `POST /runs/{id}/retry`, `POST /runs/{id}/stop`, `GET /health`; see `bem/README.md`.
- `docs/` — architecture overview, API reference, data model and Architecture Decision Records in `docs/adr/` (use `_template.md`).
- `standards/` — the DIN 4023 definition shared by `web/` and `bem/`.
- `data/` — Confidential real-project sample data (borehole PDFs/images/docx, format standards). Restricted to hackathon use and must be deleted after the event; never copy, commit, or send it to external services. Agents may read it locally. Note that the pipeline sends pages to an external LLM, so never run it on `data/`.

Each part has its own `README.md` (purpose, development setup, technology choices); the root `README.md` covers what the application does, the architecture and the production setup. Keep them in sync when behaviour changes.

## Domain context

From `challenge-presentation.pdf` (Herrenknecht kickoff slides). Boreholes are usually the only accurate description of the subsurface and drive tunnel boring machine (TBM) design; the goal is to turn legacy borehole logs into a structured, searchable base that feeds geology into TBM design.

- **Input:** borehole logs (see `data/BoreholeData/`) that are unstructured, multilingual (English, French, Spanish, …), use local geology terms/abbreviations, vary in format by company and decade, range from scanned paper to native digital, and carry meaning in colour and hatch patterns (colour vs. B/W).
- **Fields to extract per log:** elevation (absolute height of the borehole start), depth intervals (where each layer begins and ends), age/stratigraphy (formation abbreviations and colour codes), and rock type/lithology (with pattern and colour). Plus metadata: location, date, elevation.
- **Challenge pipeline:** OCR (scans and PDFs) → extract (depth, lithology, stratigraphy) → metadata → map & profile visualisation of boreholes → search (find the right log quickly). The slides name the Baden-Württemberg borehole map (bohrungen.lgrb-bw.de) as an example of the target visualisation.
- Data security is called out as a requirement across every step, which is consistent with the confidential nature of `data/`.

## ADRs

Architecture Decision Records capture important architectural decisions (e.g. choice of extraction approach, data model, libraries) and the reasoning behind them. They live in `docs/adr/` as one markdown file per decision, copied from `docs/adr/_template.md`.

- Each file starts with front matter (`id`, `date`, `author`, `title`), followed by the sections: Context, Decision, Pros, Cons, Alternatives, Consequences, References.
- Check `docs/adr/` before making a significant architectural choice, and when making a new one, write an ADR for it instead of leaving the rationale only in chat or commit messages.
- Keep the ADR set lean and current: when a decision stops being true (replaced by a later, named ADR, or by a wholesale pivot that makes a whole batch of older ADRs moot), delete the superseded ADR file outright rather than leaving it as cross-reference clutter users have to chase through. Only keep an old ADR around if it still carries real rationale someone would want later (e.g. a genuinely rejected alternative that could resurface) — judge case by case. When you delete or renumber an ADR, fix every other ADR/doc that cross-references it by number.

## Commands

A Postgres/PostGIS instance is required (`docker compose up -d db`). Full stack: `cp .env.example .env`, set `SECRET_KEY_BASE` and the AI credentials, then `docker compose up --build` (UI on `localhost:3001`).

API (run in `api/`):

- `mix setup` — deps + create/migrate/seed DB
- `mix phx.server` — dev server on localhost:4000
- `mix test` (auto creates/migrates DB); single file: `mix test test/path_test.exs`; rerun failures: `mix test --failed`
- `mix precommit` — compile with warnings-as-errors, unlock unused deps, format, test. Run when finished with changes.

Web (run in `web/`):

- `pnpm install`, `pnpm dev`
- `pnpm check` (svelte-check), `pnpm lint` (prettier + eslint), `pnpm format`
- No test runner is configured.

Pipeline (run in `bem/`; needs `uv`, poppler and an OpenRouter key; the `claude` CLI backend (`BEM_AI=claude_cli`) is development only):

- `uv sync`, `cp .env.example .env`
- `uv run python -m pipeline.server` — HTTP service on localhost:8000; `uv run python -m pipeline path/to/report.pdf` — one-off run
- `uv run python -m unittest discover tests`

## Conventions

- `api/AGENTS.md` holds the Phoenix/Elixir/Ecto rules; follow it. Notable: use `Req` for HTTP (not HTTPoison/Tesla/httpc); generate migrations with `mix ecto.gen.migration`; don't put programmatically-set fields like `user_id` in `cast`.
- Web data access follows ADR-0009: UI → service (`web/src/lib/services`) → repository interface (`web/src/lib/repositories`, API or mock), wired in one composition root (`createServices` in `services/index.ts`). UI code must not import repositories (ESLint enforces it). All data comes from the API (ADR-0029; `pnpm dev` needs the API on localhost:4000, reached via the Vite proxy at `/api`). The faker-based borehole/search mock repositories in `repositories/mock/` are kept but not wired in.
- `web/AGENTS.md` expects the Svelte MCP tools (`list-sections`, `get-documentation`, `svelte-autofixer`) to be used when writing Svelte code; Svelte skills live in `web/.github/skills/`.

- `bem/` talks to the API only over HTTP (never the database or storage directly); stage status, retries and run outcome live in `pipeline_runs` / `exec_stages` (ADR-0034, ADR-0035, ADR-0040, ADR-0044).

## Source of truth

`api/` owns the data model and API response shape (see `docs/elixir-backend-borehole-pipeline.md` and `docs/adr/`). If `web/`'s existing types or mock data disagree with what the backend actually defines/returns, the backend wins — update the frontend's types/mock data to match it, not the other way around. See ADR-0023.
