---
id: ADR-0025
date: 2026-10-17
author: Kasimir Uihlein
title: API-side paging, filtering and ranked search; place, client and document details; generated mock data
---

# ADR-0025 – API-side paging, filtering and ranked search; place, client and document details; generated mock data

## Context

The first API endpoints returned every borehole unpaged, so the web app had briefly done its own paging, sorting and filtering client-side over the full response. The frontend also lacked fields it shows (place, client, document pages and size), unknown ids returned HTML error pages, and the database had only 10 seeded boreholes. The project is a hackathon prototype; the dataset is capped at 10 000 boreholes, so production-grade scaling is not a goal.

## Decision

- **Paging, filtering, sorting in the API.** `GET /api/boreholes` and `/search` accept `q`, `bbox`, `verified`, `drilled_from`/`drilled_to`, `min_depth`/`max_depth`, `sort` (`-` for descending), `limit` (≤ 10 000) and `offset`. The response stays a GeoJSON `FeatureCollection` with `total`, `limit`, `offset` as foreign members, so the map keeps working. `view=points` returns only id, name and verified.
- **Ranked search with `ILIKE`.** Replaced by the search query language of ADR-0042 (name, place and date, trigram indexes, autocorrection); layer text is no longer searched and there is no snippet.
- **New columns.** `boreholes.place` and `boreholes.client` (both appear on logs as location/site and "Auftraggeber"), `documents.page_count` and `documents.size_bytes`. The layer foreign key now cascades on borehole delete.
- **JSON errors.** Unknown and malformed ids return `404` with `{ errors: { detail } }` through a fallback controller; invalid parameters return `400`.
- **Mock data.** `Api.MockData` generates up to 10 000 deterministic boreholes with layers and documents in the local languages of 11 countries (`mix boreholes.mock`, and from the seeds via `MOCK_BOREHOLES`). Seeded and generated rows are marked in `metadata.source` so seeds can be re-run without duplicates.
- **No document download.** Serving source files would contradict the confidentiality rule in ADR-0014 and the pipeline doc; documents stay metadata-only in the API.

The web's API repository passes all parameters through instead of filtering locally.

## Pros

- One request per page; the browser no longer downloads every borehole for a list page.
- The frontend's domain types are fully backed by the API except the download link.
- A realistic, multilingual dataset of any size up to the cap in seconds.

## Cons

- Fixed score weights are arbitrary.
- `place` and `client` are not yet filled by the extraction pipeline (`bem/`); only seeds and mock data set them.

## Alternatives

- **Postgres full-text search (`tsvector`, `ts_rank`):** better ranking and speed, but language configuration for five languages is more work than the prototype needs.
- **A separate JSON list endpoint with `{data, total}`:** cleaner than GeoJSON foreign members, but two shapes for the same data; the map and the list would diverge.
- **A Faker library for mock data:** an extra dependency for little gain; the hand-written vocabulary keeps texts geologically plausible.

## Consequences

- The extraction pipeline should fill `place` and `client` when it posts boreholes.
- Layer colour, stratigraphy and petrography stay free text; the web parses them best-effort. Structured columns remain open.
- `docs/api-reference.md` documents the contract.

## References

- ADR-0009, ADR-0014, ADR-0023
- docs/api-reference.md
