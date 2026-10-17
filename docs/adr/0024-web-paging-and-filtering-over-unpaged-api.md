---
id: ADR-0024
date: 2026-10-17
author: Kasimir Uihlein
title: Web pages, filters and sorts boreholes client-side until the API supports it
---

# ADR-0024 – Web pages, filters and sorts boreholes client-side until the API supports it

## Context

ADR-0009 assumed endpoints that return paged lists with a `total`, plus `search`, filter and `sort` parameters. The API that now exists (`docs/api-reference.md`) differs, and per ADR-0023 the backend is the source of truth:

- `GET /api/boreholes` returns a GeoJSON `FeatureCollection` with every borehole, optionally limited by `bbox`. No pagination, sorting, or filters.
- `GET /api/boreholes/search?q=` returns the same shape for matches in name, external id and layer stratigraphy. No ranking or paging.
- `GET /api/boreholes/:id` returns `{ data }` with `layers` and `documents` (no download URL).

## Decision

`ApiBoreholeRepository` and `ApiSearchRepository` keep the interfaces from ADR-0009 (UI and services do not change) and implement paging, sorting and the filters `verified`, drilling date range and depth range in the repository, on the full response. Text search uses `/boreholes/search`. Search hits have no `score`. Documents have no `url`. `totalDepth` can be `null`.

## Pros

- No change in UI or services; the API can add server-side paging later by changing one class.
- Works today with the endpoints that exist.

## Cons

- Every page request downloads all boreholes, which does not scale beyond a few thousand records.
- Text search differs between mock (also matches place and layer descriptions) and API (name, external id, stratigraphy).

## Alternatives

- Wait for server-side paging: blocks the UI work.
- Cache the full list in the browser: faster paging, but stale data and more state. Possible later inside the repository.

## Consequences

- The backend gaps are tracked in the hand-over list to the backend engineer; when they are closed, `list` and `search` in the API repositories should pass the parameters through instead of filtering locally.

## References

- ADR-0009, ADR-0023, docs/api-reference.md
