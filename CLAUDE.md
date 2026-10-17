# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon project (Herrenknecht challenge): automated extraction and standardisation of drilling/borehole data into a global geodatabase. Monorepo with two independent apps:

- `api/` — Phoenix 1.8 JSON API (Elixir, Ecto, PostGIS, Bandit). Borehole list/search/detail endpoints are documented in `docs/api-reference.md`; `mix boreholes.mock --count N` (max 10000) generates mock data.
- `web/` — SvelteKit 3 / Svelte 5 frontend (TypeScript, Tailwind 4, pnpm). Currently scaffold only (`src/routes/`).
- `bem/` — Python extraction pipeline (triage → OCR → translation/extraction → POST to API); see ADR-0001.
- `docs/` — Architecture Decision Records in `docs/adr/` (use `_template.md`).
- `data/` — Confidential real-project sample data (borehole PDFs/images/docx, format standards). Restricted to hackathon use and must be deleted after the event; never copy, commit, or send it to external services. Agents may read it locally.

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
- An ADR documents a decision at the time it was made; to change a decision, add a new ADR that references the old one rather than rewriting history.

## Commands

A Postgres instance is required (docker or local).

API (run in `api/`):
- `mix setup` — deps + create/migrate/seed DB
- `mix phx.server` — dev server on localhost:4000
- `mix test` (auto creates/migrates DB); single file: `mix test test/path_test.exs`; rerun failures: `mix test --failed`
- `mix precommit` — compile with warnings-as-errors, unlock unused deps, format, test. Run when finished with changes.

Web (run in `web/`):
- `pnpm install`, `pnpm dev`
- `pnpm check` (svelte-check), `pnpm lint` (prettier + eslint), `pnpm format`
- No test runner is configured.

## Conventions

- `api/AGENTS.md` holds the Phoenix/Elixir/Ecto rules; follow it. Notable: use `Req` for HTTP (not HTTPoison/Tesla/httpc); generate migrations with `mix ecto.gen.migration`; don't put programmatically-set fields like `user_id` in `cast`.
- Web data access follows ADR-0009: UI → service (`web/src/lib/services`) → repository interface (`web/src/lib/repositories`, API or mock). UI code must not import repositories (ESLint enforces it). `PUBLIC_DATA_SOURCE=mock|api` selects the implementation (default `mock`; `pnpm dev:api` runs against the API on localhost:4000 via the Vite proxy); mock data lives in `repositories/mock/mock-data.ts` (faker).
- `web/AGENTS.md` expects the Svelte MCP tools (`list-sections`, `get-documentation`, `svelte-autofixer`) to be used when writing Svelte code; Svelte skills live in `web/.github/skills/`.

## Source of truth

`api/` owns the data model and API response shape (see `docs/elixir-backend-borehole-pipeline.md` and `docs/adr/`). If `web/`'s existing types or mock data disagree with what the backend actually defines/returns, the backend wins — update the frontend's types/mock data to match it, not the other way around. See ADR-0023.

