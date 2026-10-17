---
id: ADR-0016
date: 2026-10-17
author: jl
title: raw_extraction stores the unmodified extraction-service response as jsonb
---

# ADR-0016 – raw_extraction stores the unmodified extraction-service response as jsonb

## Context

Borehole profiles reach `api/` via an external OCR/extraction service (a classic OCR engine, or more likely an LLM-vision service given the handwritten sources — not yet chosen, see the Elixir backend task doc's "Open Questions"). Its response format is unknown and will vary by provider. `documents` and the eventual `boreholes`/`borehole_layers` rows need to exist in a fixed, typed schema regardless.

## Decision

Split ingestion into two phases:

1. **Capture**: whatever JSON the extraction service returns is decoded into an Elixir map and stored verbatim in `documents.raw_extraction` (Ecto `:map`, Postgres `jsonb`) — no parsing, no field mapping, nothing discarded.
2. **Standardisation** (Task 3, not yet built): a separate step reads `raw_extraction` back out and maps the relevant parts into the typed `boreholes`/`borehole_layers` columns, doing unit conversion, coordinate reprojection and vocabulary normalisation along the way.

## Pros

- Decouples "which extraction service we use" from "what our DB schema looks like" — the service can be chosen/changed without needing the final schema decided first, and vice versa.
- Standardisation logic can be re-run against already-captured raw data if it improves later, without repeating the (likely slow/costly) extraction call.
- Fields the service returns but that don't (yet) map to a column are preserved rather than silently dropped during mapping.
- A reviewer can compare `raw_extraction` against the standardised fields to check the mapping was done correctly.

## Cons

- `raw_extraction` has no schema of its own, so code reading it must handle missing/differently-shaped keys defensively until the service and its response format are finalised.
- Two-phase processing means a borehole isn't immediately queryable right after the extraction call — it only exists in `boreholes`/`borehole_layers` once standardisation has run.

## Alternatives

- Map the extraction service's response directly into `boreholes`/`borehole_layers` at capture time — rejected: couples the schema to a specific service's response shape, and any field the service provides but the schema doesn't yet have a column for would be lost instead of preserved.

## Consequences

- Task 3 (Standardisation) is the only place that reads `raw_extraction` to populate `boreholes`/`borehole_layers`; nothing else should depend on its internal shape, since it isn't fixed.

## References

- docs/elixir-backend-borehole-pipeline.md
- ADR-0005 (same raw-provenance pattern on the `bem/` pipeline side)
- ADR-0011
