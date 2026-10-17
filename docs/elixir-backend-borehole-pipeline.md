# Elixir Backend Task: Borehole Data Pipeline & Map API

## Challenge Context

Herrenknecht needs reliable subsurface information for tunnel boring machine planning. Borehole profiles from tunnel/mining projects worldwide exist as PDFs, scans and photos (partially handwritten), in different formats and languages. They currently have to be analysed manually.

**Goal:** Automatically extract borehole profiles from PDFs/scans/images, convert them into a standardised format, georeference them, and store them in a central database that is searchable via an interactive world map (see `web/` SvelteKit + MapLibre frontend).

**Success metric:** reliable extraction → standardisation → georeferencing → storage, searchable in the DB and displayed on the map, validated against the provided sample dataset.

This document scopes the **`api/` Phoenix backend** work. The frontend (`web/`, a SvelteKit app) renders boreholes on a MapLibre map and a detail view similar to the attached screenshot (borehole profile column + stratigraphy table + metadata + mini-map).

---

## Data Model

Add `PostGIS` support (`geo`, `geo_postgis` deps) for coordinate storage and spatial queries.

### `documents`
Source file metadata (one row per uploaded PDF/scan/image).

| field | type | required? | notes |
|---|---|---|---|
| `id` | `binary_id` | yes (PK) | |
| `original_filename` | `string` | yes | |
| `storage_path` | `string` | yes | path/URL to the stored file |
| `mime_type` | `string` | no | e.g. "application/pdf", "image/jpeg" |
| `source_country` | `string` | no | optional, if known |
| `status` | `enum` | yes (default `pending`) | `pending`, `processing`, `extracted`, `failed`, `reviewed` |
| `page_count` | `integer` | no | ADR-0025 |
| `size_bytes` | `integer` | no | ADR-0025 |
| `raw_extraction` | `map` (`jsonb`) | no | unmodified output from the OCR service |
| `inserted_at` / `updated_at` | | yes (auto) | |

> **Confidentiality**: source documents are confidential and must never be published, committed to git, or sent to external services. Inside the application they may be shown (ADR-0026): `GET /api/documents/:id/file` serves a stored file to the `web/` frontend. `storage_path` and `raw_extraction` never appear in any JSON response — a document's JSON representation only ever exposes `id`, `original_filename`, `mime_type`, `source_country`, `status`, `page_count`, `size_bytes` and `has_file` (whether a file is actually stored for it; generated mock documents have `has_file: false`). For the hackathon this is local disk; swap for an S3-compatible bucket if persistence across deploys is needed.

> **Storage layout**: `api/priv/uploads/` is a staging inbox — files placed there are NOT yet tracked in `documents` (used for manually-dropped sample data; `mix documents.backfill` processes it). `api/priv/storage/` is the managed store: files live there as `<document_id><ext>` (flat, no subfolders), so a file's `documents` row can always be found from its filename. Both directories are gitignored, outside `priv/static` so Phoenix never serves them publicly. The real upload endpoint (Task 2) should write straight into `priv/storage/` and skip the inbox entirely.

### `boreholes`
One row per borehole (`Stammdaten` in the screenshot).

| field | type | required? | notes |
|---|---|---|---|
| `id` | `binary_id` | yes (PK) | |
| `name` | `string` | yes | e.g. "B 1/59 Schönberg..." |
| `external_id` | `string` | no | project/source-assigned ID (e.g. "HOLE NO: BH_AB01"), not unique — different projects can reuse IDs |
| `purpose` | `string` | no | "Bohrzweck" |
| `place` | `string` | no | location/site name as it appears on the log (ADR-0025) |
| `client` | `string` | no | "Auftraggeber" (ADR-0025) |
| `drilling_method` | `string` | no | "Bohrart" |
| `drilled_at` | `date` | no | "Bohrdatum" / "DATE STARTED" |
| `end_date` | `date` | no | "DATE COMPLETED" — a borehole can span multiple days |
| `location` | `geometry(Point, 4326)` | no | WGS84 lon/lat for the map |
| `source_coordinate_system` | `string` | no | e.g. "32U UTM", kept for traceability |
| `source_coordinate_raw` | `string` | no | original coordinate string before conversion |
| `total_depth_m` | `decimal` | no | "Endteufe", vertical depth |
| `borehole_length_m` | `decimal` | no | length along the hole axis; differs from `total_depth_m` for angled/directional boreholes |
| `elevation_m` | `decimal` | no | "Ansatzhöhe" |
| `groundwater_level_m` | `decimal` | no | depth to groundwater below surface, in meters — one value per borehole, not per layer |
| `verified` | `boolean` | yes (default `false`) | "LGRB geprüft" equivalent — reviewed by a human |
| `metadata` | `map` (`jsonb`) | yes (default `{}`) | open key/value store for anything not covered by a fixed column (e.g. rig type, contractor, driller) |

> **documents ↔ boreholes is many-to-many**, via the join table `borehole_documents` (`borehole_id`, `document_id`, unique on the pair). A single scanned report can cover several boreholes, and the same borehole can be documented across multiple files (e.g. a scan + a typed follow-up report). Each link has a `role`: `original` (the one log the borehole was extracted from, at most one per borehole, enforced by a partial unique index) or `additional` (ADR-0028). Link documents with `Api.Boreholes.attach_documents/3` so the role is set, not with `put_assoc`, and not with a `document_id` column.

### `borehole_documents`
Join table for the `boreholes` ↔ `documents` many-to-many (ADR-0013). A schema module (not a bare table-name string) backs `join_through`, so Ecto populates timestamps on `put_assoc` instead of raising a `not_null_violation`.

| field | type | required? | notes |
|---|---|---|---|
| `id` | `binary_id` | yes (PK) | |
| `borehole_id` | `references(:boreholes)` | yes | |
| `document_id` | `references(:documents)` | yes | |
| `role` | `string` | yes (default `additional`) | `original` (the one log the borehole was extracted from) or `additional`; set via `Api.Boreholes.attach_documents/3`, not `put_assoc` (ADR-0028) |
| `inserted_at` / `updated_at` | | yes (auto) | |

Unique index on `(borehole_id, document_id)`; partial unique index on `borehole_id` where `role = 'original'` (at most one original document per borehole, ADR-0028); index on `document_id` for the reverse lookup.

### `borehole_layers`
Stratigraphy rows (the table in the screenshot: von/bis/Stratigraphie/Petrographie/Farbe).

| field | type | required? | notes |
|---|---|---|---|
| `id` | `binary_id` | yes (PK) | |
| `borehole_id` | `references(:boreholes)` | yes | set programmatically, not user input; `on_delete: :delete_all` (ADR-0025) — deleting a borehole deletes its layers |
| `position` | `integer` | yes | ordering (1, 2, 3, ...) |
| `depth_from_m` | `decimal` | yes | |
| `depth_to_m` | `decimal` | yes | must be greater than `depth_from_m` |
| `stratigraphy` | `string` | no | geological formation |
| `petrography` | `string` | no | free text, e.g. "Kies [gerundet] (steinig, ...)" |
| `color` | `string` | no | |
| `raw_text` | `string` | no | original OCR text for this row, for QA |
| `metadata` | `map` (`jsonb`) | yes (default `{}`) | open key/value store for per-layer values not covered by a fixed column (e.g. RQD %, SPT) |

Keep `raw_text` / `raw_extraction` fields everywhere plausible — given handwritten sources, this data will need to be re-verified, so never throw away the source text.

---

## Pipeline Stage Tracking (implemented, ADR-0030)

### Motivation

`bem/`'s pipeline has five stages (OCR → translation/labeling → triage → extraction → output, ADR-0001). Today the only intermediate visibility is a local, gitignored, per-developer JSON file cache (ADR-0006) — nothing is visible to the rest of the team, and nothing survives past a developer's machine. `documents.raw_extraction` (ADR-0016) is a single JSONB blob written at the very end of ingestion, not a per-stage trace.

Goal: for any `document`, be able to inspect what each stage actually produced — including where triage split one document into several borehole candidates, and which of those candidates extraction succeeded or failed on.

### Decisions (confirmed with the team)

- **Write path**: `bem/` reports stage results to new `api/` endpoints (not direct DB access) — the API stays the only thing that touches Postgres, consistent with ADR-0017/0023.
- **History**: latest run only. A rerun overwrites/replaces the previous stage data for that document rather than keeping every past attempt. This keeps the schema simple at the cost of before/after comparisons across BEM code changes.
- **Granularity**: relational, not a JSON blob — triage's one-document-to-many-boreholes fan-out gets its own rows so individual candidates are filterable/queryable.
- **Relation to ADR-0006**: additive. The local file cache stays for fast BEM-local iteration; these tables are for cross-team troubleshooting once a run has reached (or reported to) the API.
- **Confidentiality**: identical rule to `storage_path`/`raw_extraction` (ADR-0014) — none of this is ever serialised in a public API response. Debug/internal visibility only.

### Proposed tables

Because only the latest run is kept, these are modelled as overwrite-on-rerun (upsert or delete-and-reinsert), not an append-only history.

#### `pipeline_stage_runs`
One row per `(document, stage)` for the two stages that are still document-level (haven't fanned out into per-borehole candidates yet). A rerun upserts on `(document_id, stage)`.

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | PK |
| `document_id` | `references(:documents)` | |
| `stage` | `string` | `"ocr"` \| `"translation"` |
| `status` | `string` | `"ok"` \| `"error"` |
| `output` | `map` (`jsonb`) | e.g. OCR: `{"markdown": ...}`; translation: `{"translated_markdown": ..., "source_language": ..., "translate_errors": [...]}` |
| `error` | `string` | nullable |
| `started_at` / `finished_at` | `utc_datetime` | |

Unique index on `(document_id, stage)`.

#### `triage_sections`
One row per borehole candidate that triage found in the document — the fan-out point. A rerun deletes all existing sections for that `document_id` and reinserts the new set (count/content can change between runs).

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | PK |
| `document_id` | `references(:documents)` | |
| `section_index` | `integer` | 0-based position within the document |
| `borehole_id_guess` | `string` | nullable — the raw label triage matched, e.g. `"BH-2"` |
| `raw_markdown` | `string` | this section's slice of the translated markdown |
| `translate_errors` | `{array, :string}` (`jsonb`) | errors found within this section |

Unique index on `(document_id, section_index)`.

#### `extraction_results`
One row per `triage_section` (1:1). `on_delete: :delete_all` from `triage_sections`, so a rerun's section cleanup cascades automatically — no separate overwrite logic needed here.

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | PK |
| `triage_section_id` | `references(:triage_sections)` | unique (1:1) |
| `status` | `string` | `"ok"` \| `"error"` |
| `extracted_fields` | `map` (`jsonb`) | the candidate `Borehole`/`Bohrung` fields as extracted |
| `validation_issues` | `map` (`jsonb`) | e.g. depth-range or missing-field issues |
| `error` | `string` | nullable |

#### `sink_results`
One row per `extraction_result` (1:1), cascading the same way.

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | PK |
| `extraction_result_id` | `references(:extraction_results)` | unique (1:1) |
| `target` | `string` | `"api"` \| `"json"` \| `"print"` |
| `success` | `boolean` | |
| `response_status` | `integer` | nullable, HTTP status if `target == "api"` |
| `created_borehole_id` | `references(:boreholes)` | nullable — set once the API has actually created the borehole |
| `error` | `string` | nullable |

### API endpoints (implemented, ADR-0030)

- `PUT /api/documents/:document_id/pipeline_stages/:stage` — upsert the OCR or translation result for a document
- `PUT /api/documents/:document_id/triage_sections` — replace all triage sections for a document in one call (body: list of sections)
- `PUT /api/documents/:document_id/triage_sections/:section_index/extraction_result` — upsert the extraction result for one section
- `PUT /api/documents/:document_id/triage_sections/:section_index/sink_result` — upsert the sink result for one section
- `GET /api/documents/:document_id/pipeline_trace` — the full trace for a document (stage runs + triage sections, each with its extraction/sink result) in one nested response, for troubleshooting

See `bem/API_INTEGRATION.md` for the full contract (bodies, call order) from `bem/`'s side; BEM-side changes to actually call these are out of scope for `api/`.

---

## Task Breakdown

### 1. Schema & migrations
- `mix ecto.gen.migration create_documents|create_boreholes|create_borehole_layers`
- Enable `postgis` extension in a migration (`execute "CREATE EXTENSION IF NOT EXISTS postgis"`)
- Add a GiST index on `boreholes.location` for fast bbox queries
- Ecto schemas + changesets with validation (depth_from < depth_to, lat/lon bounds, etc.)

### 2. Ingestion pipeline
> **Superseded by ADR-0031** for the creation step: there is no external extraction service to poll (`bem/` runs extraction itself and reports results directly, ADR-0030), so the design below was not built. `POST /api/boreholes` (synchronous, see Task 4) is what exists today. The upload endpoint also doesn't exist yet — see `bem/API_INTEGRATION.md` for how `bem/` gets a `document_id` without one.

- ~~Upload endpoint (`POST /api/documents`) accepting a file, stores it (local disk for the hackathon, or S3-compatible bucket), creates a `documents` row with `status: :pending`~~
- ~~Background job (use `Oban` — add dep) that:~~
  1. ~~Calls the external extraction service via `Req` (per `AGENTS.md`, avoid `:httpoison`/`:tesla`)~~
  2. ~~Stores the raw JSON result in `documents.raw_extraction`~~
  3. ~~Runs the **standardisation** step (see below) to populate `boreholes` + `borehole_layers`~~
  4. ~~Sets `documents.status` to `:extracted` or `:failed`~~
- ~~Make the job idempotent/retryable (Oban gives this for free) since OCR calls can fail or time out~~

### 3. Standardisation
- Normalise units (cm/m), decimal separators (`,` vs `.`), depth ranges, and language-specific stratigraphy/petrography terms into a consistent vocabulary (consider a lookup/mapping table rather than hardcoding, so new terms from new countries can be added)
- Convert source coordinates (UTM zones, local grids, DMS, etc.) to WGS84 lon/lat for storage — `Geo` + a conversion lib (e.g. shell out to `proj` or use a pure-Elixir UTM conversion) is sufficient for the hackathon scope

### 4. Map/Search API (consumed by `web/`) — implemented, see `docs/api-reference.md`
- `GET /api/boreholes` → GeoJSON `FeatureCollection`, with `bbox`, ranked text search (`q`), filters (`verified`, `drilled_from`/`drilled_to`, `min_depth`/`max_depth`), `sort`, paging (`limit`/`offset`, capped at 10 000) and `view=points` for a lightweight map payload (ADR-0025)
- `GET /api/boreholes/:id` → full detail (Stammdaten + ordered `borehole_layers` + confidentiality-filtered `documents`); `404` JSON for an unknown or malformed id
- `GET /api/boreholes/search` → same shape as the list endpoint, plus `score`/`snippet` per feature (ADR-0025)
- `GET /api/documents/:id/file` → streams a document's stored file for in-app viewing, `?download=1` for an attachment (ADR-0026, supersedes the "never exposed" part of ADR-0014)
- `POST /api/boreholes` → creates a borehole + its layers synchronously, optionally linked to an existing document (ADR-0031, supersedes the async design in Task 2 above)
- Errors are JSON (`{ errors: { detail } }`) via `action_fallback ApiWeb.FallbackController`: `400`/`404` for GETs, `422` with field errors for `POST /api/boreholes` changeset failures
- `Api.MockData` + `mix boreholes.mock --count N` (and `MOCK_BOREHOLES` in seeds) generates up to 10 000 deterministic boreholes/layers/documents for load-testing paging and search without real data

### 5. Review/QA workflow (nice-to-have if time allows)
- Minimal endpoint/LiveView to list unverified boreholes and let a human correct depth/stratigraphy/coordinates before marking `verified: true`
- How a borehole gets flagged for review (confidence scoring, AI cross-check, etc.) is still an open decision — not scoped yet

---

## Suggested New Dependencies (`api/mix.exs`)

```elixir
{:geo, "~> 3.6"},
{:geo_postgis, "~> 3.6"},
{:oban, "~> 2.19"}
```

`Req` is already included — use it for calling the external extraction service instead of adding an HTTP client.

---

## Out of Scope / Explicitly Not This Task
- The actual OCR/handwriting-recognition model — assume it's an external service/API that returns structured-ish JSON (coordinate, depth table, free text) per document; the Elixir task is everything downstream of that call plus the orchestration around it
- Map rendering/interaction (MapLibre) lives in `web/`

## Open Questions
- Format of the external extraction service's response (needs to be agreed with whoever builds/wraps the OCR step)
- Which coordinate systems appear in the real dataset (affects the georeferencing conversion logic)
- Expected data volume (affects whether Oban + simple polling is enough, or whether a queue/worker pool is needed)
