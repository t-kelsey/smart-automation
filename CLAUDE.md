# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon project (Herrenknecht challenge): automated extraction and standardisation of drilling/borehole data into a global geodatabase. Monorepo with two independent apps:

- `api/` — Phoenix 1.8 JSON API (Elixir, Ecto, Postgres, Bandit). Currently scaffold only: the `/api` scope in `api/lib/api_web/router.ex` has no routes yet.
- `web/` — SvelteKit 3 / Svelte 5 frontend (TypeScript, Tailwind 4, pnpm). Currently scaffold only (`src/routes/`).
- `docs/` — Architecture Decision Records in `docs/adr/` (use `_template.md`).
- `data/` — Confidential real-project sample data (borehole PDFs/images/docx, format standards). Restricted to hackathon use and must be deleted after the event; never copy, commit, or send it to external services.

## ADRs

Architecture Decision Records capture important architectural decisions (e.g. choice of extraction approach, data model, libraries) and the reasoning behind them. They live in `docs/adr/` as one markdown file per decision, copied from `docs/adr/_template.md`.

- Each file starts with front matter (`id`, `date`, `author`, `title`), followed by the sections: Context, Decision, Pros, Cons, Alternatives, Consequences, References.
- No ADRs exist yet besides the template. Check `docs/adr/` before making a significant architectural choice, and when making a new one, write an ADR for it instead of leaving the rationale only in chat or commit messages.
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
- `web/AGENTS.md` expects the Svelte MCP tools (`list-sections`, `get-documentation`, `svelte-autofixer`) to be used when writing Svelte code; Svelte skills live in `web/.github/skills/`.
