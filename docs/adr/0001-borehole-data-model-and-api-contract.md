---
id: ADR-0001
date: 2026-11-18
author: Tyler Kelsey
title: Borehole data model, ingestion contract and API as source of truth
---

# ADR-0001 – Borehole data model, ingestion contract and API as source of truth

## Context

Borehole logs are multilingual, arrive as scans, PDFs or images, and often yield only part of their fields. The database has to store extracted profiles without losing the source text, and the API is the contract every client uses. Frontend mock data existed before the API; it must not define the schema.

## Decision

**Tables** (UUID primary keys)

- `boreholes`: name, external id, place, client, drilling metadata, `location geometry(Point, 4326)` (nullable), the raw coordinates and `source_coordinate_system` for traceability, depth/elevation/groundwater fields, `verified`, and an open `metadata` jsonb map.
- `borehole_layers`: one row per interval, ordered by `position`, with `depth_from_m` and `depth_to_m` (the latter must be greater than the former), free-text `stratigraphy`, `petrography` and colour, and a `metadata` jsonb map.
- `documents`: file metadata (storage in ADR-0002) plus `raw_extraction` jsonb.
- `borehole_documents`: many-to-many join with `role` `original` or `additional`. A partial unique index allows at most one original per borehole. The role sits on the link, so one file can be the original of one borehole and additional for another.
- Only `boreholes.name`, `layers.position`, the two depths and the depth check are required. Everything else is nullable.

**Coordinates.** The pipeline sends coordinates as written in the source plus an EPSG code. The API stores the raw values and builds the WGS84 point with `ST_Transform(ST_SetSRID(ST_MakePoint(x, y), epsg), 4326)`. Without coordinates or EPSG the location is null and the borehole is still stored. Choosing the right EPSG code (e.g. the UTM zone) is the extraction step's job; a wrong code silently places the borehole in the wrong spot.

**Raw extraction.** Ingestion is one pass: map the extraction response into boreholes and layers, insert them in one transaction, and store the unmodified response in `documents.raw_extraction` for debugging. Nothing reads it back, and it never appears in an API response.

**Ingestion endpoint.** `POST /api/boreholes` takes `{borehole, layers, document_id}` and creates the borehole synchronously in one transaction. `x`, `y` and `epsg` may replace `location`. `layers[].position` defaults to list order. `document_id` attaches the borehole as its original. Responses: `201` (same shape as `GET /api/boreholes/:id`), `422` with field errors, `400` for an unknown document. It is not idempotent; the pipeline calls it once per borehole. No upload-plus-background-job design (Oban) is built or planned.

**Read API.** `GET /api/boreholes` and `/search` return a GeoJSON `FeatureCollection` with `total`, `limit` and `offset` as foreign members, so the map and the list share one shape. Filters: `bbox`, `verified`, drilled date range, depth range; `sort` with `-` for descending; `limit` up to 10 000; `view=points` returns only id, name and verified. Unknown ids return `404` JSON, invalid parameters `400`. Search syntax is in ADR-0003.

**Mock data.** `Api.MockData` generates up to 10 000 deterministic boreholes with layers and documents in the local languages of 11 countries (`mix boreholes.mock`, seeds via `MOCK_BOREHOLES`). Generated rows are marked in `metadata.source`.

**Deferred.** Stratigraphy and petrography stay free text; no lookup tables. The internationally standardised ICS `geologic_age` is the intended cross-region comparable field, not yet implemented.

**Source of truth.** The API's data model and JSON responses win. Where frontend types or mock data disagree, the frontend changes. A field the frontend needs but the backend lacks is added to the backend deliberately, with an ADR if non-trivial.

## Pros

- Partial extraction does not block ingestion; most fields can be absent.
- Raw source text is kept, so bad extractions can be corrected without re-running OCR.
- One request shape serves both the map and the list.
- The `location` column plus a GiST index supports bounding-box queries for the map.
- One authoritative schema instead of drifting frontend and backend shapes.

## Cons

- Pervasive nullability: every consumer must handle missing data.
- Open `metadata` jsonb maps have no schema and can become inconsistent.
- `raw_extraction` has no schema, so any future reprocessing must handle differently shaped keys defensively; there is no built-in replay.
- Free-text layer fields cannot be filtered reliably across regions until lookup tables exist.
- The extraction step must supply `place` and `client`, which are only set by seeds and mock data today.

## Alternatives

- **One denormalised table with layers as a JSON array:** rejected; loses relational queries (e.g. by stratigraphy) and per-layer depth checks.
- **One `document_id` foreign key on boreholes:** rejected; one scan often covers several boreholes and one borehole can have several files.
- **Asynchronous upload plus background job for ingestion:** not built; there is no external extraction service to wait on or retry.
- **Reproject in Python with pyproj:** rejected; adds a dependency and loses the raw values.
- **Frontend shape as the authority:** rejected; it would add unverified fields (client, cause, structured lithology) to the backend just to match a mock-up.
- **Lookup tables for stratigraphy and petrography now:** deferred; names are regionally defined and need a curated reference to match reliably.

## Consequences

- New backend data follows this model; changes to the response shape are reflected in `docs/api-reference.md` and the frontend types.
- The pipeline must set EPSG codes, the original document, and should set `place` and `client`.
- Authentication is required before the API leaves a trusted network (see ADR-0002).

## References

- `docs/api-reference.md`, `docs/data-model.md`
- `docs/elixir-backend-borehole-pipeline.md`
- `api/lib/api/boreholes/`
- `CLAUDE.md` (source of truth)
