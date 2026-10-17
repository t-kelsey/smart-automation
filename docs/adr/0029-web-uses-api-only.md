---
id: ADR-0029
date: 2026-10-17
author: Kasimir Uihlein
title: The web app reads all data from the API; mock repositories stay but are not wired in
---

# ADR-0029 – The web app reads all data from the API; mock repositories stay but are not wired in

## Context

ADR-0009 let `PUBLIC_DATA_SOURCE=mock|api` choose the repository, with `mock` as the default because the API had no data. The API now serves lists, search, details, documents and 1000+ generated boreholes (ADR-0025), so a default of `mock` means the app silently shows data that does not exist in the backend.

## Decision

- `createServices({ fetch })` always builds the API repositories. `PUBLIC_DATA_SOURCE` and the `dev:api` script are removed.
- The faker-based mock repositories and `mock-data.ts` stay in `web/src/lib/repositories/mock/` but nothing imports them. `PUBLIC_MOCK_BOREHOLES` remains because `mock-data.ts` reads it.
- The layering from ADR-0009 (UI → service → repository interface) is unchanged, so a mock can be wired back in at the composition root.

## Pros

- The app shows what the backend holds; no hidden fallback to fake data.
- One code path to test.

## Cons

- The frontend needs the API running (`pnpm dev` alone shows load errors).
- Unwired mock code can drift from the repository interface; `pnpm check` still type-checks it.

## Alternatives

- Keep the env switch with `api` as default: more config, and a mock is one wrong variable away.
- Delete the mock code: ruled out, it is useful for offline work and tests.

## Consequences

- Supersedes the data-source switch in ADR-0009.
- Developers start the API (`mix phx.server`) before the web app.

## References

- ADR-0009, ADR-0025
