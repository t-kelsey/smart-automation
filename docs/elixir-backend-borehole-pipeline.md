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

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | |
| `original_filename` | `string` | |
| `storage_path` | `string` | path/URL to the stored file |
| `source_country` | `string` | optional, if known |
| `status` | `enum` | `pending`, `processing`, `extracted`, `failed`, `reviewed` |
| `raw_extraction` | `map` (`jsonb`) | unmodified output from the OCR service |
| `inserted_at` / `updated_at` | | |

> **Confidentiality**: source documents are confidential and must never be exposed to the `web/` frontend or any public endpoint, and must never be committed to git. `documents` (including `storage_path`) is backend/review-only — the map/search API only ever returns `boreholes`/`borehole_layers`. Store uploaded files under `api/priv/uploads/` (gitignored, outside `priv/static` so Phoenix never serves them publicly) — for the hackathon this is local disk; swap for an S3-compatible bucket if persistence across deploys is needed.

### `boreholes`
One row per borehole (`Stammdaten` in the screenshot).

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | |
| `document_id` | `references(:documents)` | |
| `name` | `string` | e.g. "B 1/59 Schönberg..." |
| `purpose` | `string` | "Bohrzweck" |
| `drilling_method` | `string` | "Bohrart" |
| `drilled_at` | `date` | "Bohrdatum" |
| `location` | `geometry(Point, 4326)` | WGS84 lon/lat for the map |
| `source_coordinate_system` | `string` | e.g. "32U UTM", kept for traceability |
| `source_coordinate_raw` | `string` | original coordinate string before conversion |
| `total_depth_m` | `decimal` | "Endteufe" |
| `elevation_m` | `decimal` | "Ansatzhöhe" |
| `verified` | `boolean` | "LGRB geprüft" equivalent — reviewed by a human |

### `borehole_layers`
Stratigraphy rows (the table in the screenshot: von/bis/Stratigraphie/Petrographie/Farbe).

| field | type | notes |
|---|---|---|
| `id` | `binary_id` | |
| `borehole_id` | `references(:boreholes)` | |
| `position` | `integer` | ordering (1, 2, 3, ...) |
| `depth_from_m` | `decimal` | |
| `depth_to_m` | `decimal` | |
| `stratigraphy` | `string` | geological formation |
| `petrography` | `string` | free text, e.g. "Kies [gerundet] (steinig, ...)" |
| `color` | `string` | |
| `raw_text` | `string` | original OCR text for this row, for QA |

Keep `raw_text` / `raw_extraction` fields everywhere plausible — given handwritten sources, this data will need to be re-verified, so never throw away the source text.

---

## Task Breakdown

### 1. Schema & migrations
- `mix ecto.gen.migration create_documents|create_boreholes|create_borehole_layers`
- Enable `postgis` extension in a migration (`execute "CREATE EXTENSION IF NOT EXISTS postgis"`)
- Add a GiST index on `boreholes.location` for fast bbox queries
- Ecto schemas + changesets with validation (depth_from < depth_to, lat/lon bounds, etc.)

### 2. Ingestion pipeline
- Upload endpoint (`POST /api/documents`) accepting a file, stores it (local disk for the hackathon, or S3-compatible bucket), creates a `documents` row with `status: :pending`
- Background job (use `Oban` — add dep) that:
  1. Calls the external extraction service via `Req` (per `AGENTS.md`, avoid `:httpoison`/`:tesla`)
  2. Stores the raw JSON result in `documents.raw_extraction`
  3. Runs the **standardisation** step (see below) to populate `boreholes` + `borehole_layers`
  4. Sets `documents.status` to `:extracted` or `:failed`
- Make the job idempotent/retryable (Oban gives this for free) since OCR calls can fail or time out

### 3. Standardisation
- Normalise units (cm/m), decimal separators (`,` vs `.`), depth ranges, and language-specific stratigraphy/petrography terms into a consistent vocabulary (consider a lookup/mapping table rather than hardcoding, so new terms from new countries can be added)
- Convert source coordinates (UTM zones, local grids, DMS, etc.) to WGS84 lon/lat for storage — `Geo` + a conversion lib (e.g. shell out to `proj` or use a pure-Elixir UTM conversion) is sufficient for the hackathon scope

### 4. Map/Search API (consumed by `web/`)
- `GET /api/boreholes?bbox=minLon,minLat,maxLon,maxLat` → GeoJSON `FeatureCollection` of boreholes in view (for MapLibre clustering/markers)
- `GET /api/boreholes/:id` → full detail (Stammdaten + ordered `borehole_layers` + reference to original document) for the detail panel shown in the screenshot
- `GET /api/boreholes/search?q=...` → free-text search (name, stratigraphy, country)
- Return borehole list as GeoJSON (`Jason.Encoder` on a `%Geo.Point{}` via `geo_postgis`) so the frontend can feed it directly into a MapLibre GeoJSON source

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
