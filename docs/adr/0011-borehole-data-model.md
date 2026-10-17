---
id: ADR-0011
date: 2026-10-17
author: jl
title: Borehole data model - documents, boreholes, and borehole_layers
---

# ADR-0011 – Borehole data model - documents, boreholes, and borehole_layers

## Context

The Phoenix API needs a standardised schema to store extracted borehole profiles from multilingual, multi-format, sometimes handwritten source documents, and to serve them to a map/search API. Fields have to accommodate incomplete extraction, since not every document yields every field.

## Decision

Three core tables, all with UUID primary keys:

- `documents` — source file metadata (one row per uploaded PDF/scan/image); see ADR-0014 for storage/confidentiality handling.
- `boreholes` — one row per borehole (Stammdaten): name, drilling metadata, a PostGIS `geometry(Point, 4326)` for the standardised WGS84 location plus `source_coordinate_system`/`source_coordinate_raw` for traceability, depth/elevation/groundwater fields, `verified`, and an open `metadata` jsonb map for anything not covered by a fixed column.
- `borehole_layers` — one row per stratigraphy interval (von/bis/Stratigraphie/Petrographie/Farbe), ordered by `position`, with the same open `metadata` jsonb map.

All descriptive fields are nullable by default; only structurally required fields are enforced (`boreholes.name`; `borehole_layers.position`/`depth_from_m`/`depth_to_m`, plus `depth_to_m > depth_from_m`). `raw_text`/`raw_extraction` columns preserve the unprocessed source text alongside standardised fields, mirroring the raw-jsonb provenance pattern from ADR-0005 (bem/ pipeline) on the `api/` side.

## Pros

- Partial/incomplete extraction doesn't block ingestion — most fields can simply be absent.
- Raw source text is never discarded, so low-quality extractions can be corrected later without re-running OCR.
- `location` + a GiST index support efficient bbox queries for the map.

## Cons

- Pervasive nullability means application code (and later, the frontend) must handle missing data almost everywhere.
- Open `metadata` jsonb columns have no schema and can become inconsistent without discipline on what goes in them.

## Alternatives

- A single denormalised table per borehole with layers as a JSON array — rejected, loses relational queryability (e.g. searching by stratigraphy across layers) and simple per-layer depth validation.

## Consequences

- The map/search API only ever returns `boreholes`/`borehole_layers`; `documents` is backend/review-only (see ADR-0014).

## References

- docs/elixir-backend-borehole-pipeline.md
- ADR-0005
