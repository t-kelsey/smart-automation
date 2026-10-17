# API Reference: Boreholes (Map/Search API)

Base URL: `http://localhost:4000/api` (dev). All responses are JSON (`Content-Type: application/json`). No authentication is currently implemented. Errors always have the shape `{ "errors": { "detail": "..." } }`.

This covers the endpoints implemented so far — Task 4 ("Map/Search API") from [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md), plus `POST /api/boreholes` (ADR-0031), the document upload endpoints (ADR-0033), and the `claude_test/` pipeline submission/tracking endpoints (ADR-0034, ADR-0035, see the "Pipeline runs" section below). Uploading a document (`POST /api/documents`) no longer starts processing by itself (ADR-0035) — the frontend uploads a file, lets the user pick a per-stage model/effort `config`, then calls `POST /api/pipeline_runs` to actually submit the run and polls `GET /api/pipeline_runs/:id` for progress.

> **Confidentiality**: `documents.storage_path` and `documents.raw_extraction` are never returned by any endpoint. For a document only `id`, `original_filename`, `mime_type`, `source_country`, `status`, `page_count`, `size_bytes` and `has_file` are exposed; the file itself is served by [`GET /api/documents/:id/file`](#get-apidocumentsidfile) for use inside the application only (ADR-0026). Never publish or commit these files.

> **Prototype scale**: the dataset is capped at 10 000 boreholes. Without `limit` every match is returned in one response; `limit` may be at most 10 000.

---

## `GET /api/boreholes`

List boreholes as a GeoJSON `FeatureCollection`, with optional filters, sorting and paging. The map uses it with `view=points`, lists use `limit`/`offset`.

### Query parameters (all optional)

| Param | Format | Description |
|---|---|---|
| `bbox` | `minLon,minLat,maxLon,maxLat` | Only boreholes whose `location` intersects this envelope. |
| `q` | text | Text search, same as [`/search`](#get-apiboreholessearch); adds `score`/`snippet` and sorts by score. |
| `verified` | `true` / `false` | Only verified / unverified boreholes. |
| `drilled_from`, `drilled_to` | `YYYY-MM-DD` | Inclusive range on `drilled_at`. |
| `min_depth`, `max_depth` | number (m) | Inclusive range on `total_depth_m`. |
| `sort` | `name`, `drilled_at`, `total_depth_m`, `inserted_at`, `score`; prefix `-` for descending | Default: `name` (or `-score` when `q` is given). Missing values sort last. |
| `limit` | 1–10000 | Page size. Omit to get every match. |
| `offset` | ≥ 0 | Number of matches to skip. |
| `view` | `points` | Return only `id`, `name`, `verified` in `properties` (small response for the map). |

### Response `200 OK`

```json
{
  "type": "FeatureCollection",
  "total": 259,
  "limit": 20,
  "offset": 0,
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [9.177, 48.776] },
      "properties": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "B 1/59 Schönberg",
        "external_id": "BH_AB01",
        "purpose": "Hydrogeologische Untersuchung",
        "place": "Stuttgart",
        "client": "Stadtwerke",
        "drilling_method": "Rotary core drilling",
        "drilled_at": "1959-06-12",
        "end_date": null,
        "source_coordinate_system": "32U UTM",
        "source_coordinate_raw": "412559.379, 5315392.271",
        "total_depth_m": "18.3",
        "borehole_length_m": null,
        "elevation_m": "262.0",
        "groundwater_level_m": null,
        "verified": false,
        "metadata": {},
        "inserted_at": "2026-10-17T09:06:00Z",
        "updated_at": "2026-10-17T09:06:00Z"
      }
    }
  ]
}
```

- `total` is the number of matches across all pages; `limit` is `null` when not given. `total`, `limit` and `offset` are GeoJSON foreign members, so the response is still valid GeoJSON.
- `geometry` is `null` if the borehole has no `location` yet (e.g. not yet georeferenced).
- `properties` holds every `boreholes` column except `location` (promoted to `geometry`); layers and documents are only in the detail endpoint.
- With `q`, each feature also has `score` and `snippet` (see below).

### Response `400 Bad Request`

Returned for an invalid parameter, naming the first one:

```json
{ "errors": { "detail": "invalid bbox" } }
```

### Examples

```bash
curl "http://localhost:4000/api/boreholes?bbox=9.0,48.0,10.0,49.0"
curl "http://localhost:4000/api/boreholes?verified=true&min_depth=20&sort=-total_depth_m&limit=20&offset=40"
curl "http://localhost:4000/api/boreholes?view=points"
```

---

## `GET /api/boreholes/:id`

Full detail for a single borehole: Stammdaten + ordered stratigraphy layers + associated (confidentiality-filtered) documents. This is what the borehole detail page uses.

### Response `200 OK`

```json
{
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "B 1/59 Schönberg",
    "...": "all properties as in the list",
    "location": { "type": "Point", "coordinates": [9.177, 48.776] },
    "layers": [
      {
        "id": "b3f1...",
        "position": 1,
        "depth_from_m": "0.0",
        "depth_to_m": "3.5",
        "stratigraphy": "Neuenburg-Formation",
        "petrography": "Kies [gerundet] (steinig, schwach grobsandig)",
        "color": "grau",
        "raw_text": "0,0-3,5 Kies...",
        "metadata": {}
      }
    ],
    "documents": [
      {
        "id": "c7a2...",
        "original_filename": "B1-59_Schichtenverzeichnis.pdf",
        "mime_type": "application/pdf",
        "source_country": "Germany",
        "status": "pending",
        "page_count": 3,
        "size_bytes": 1269760,
        "has_file": true,
        "role": "original"
      }
    ]
  }
}
```

`layers` is always ordered by `position` ascending. `documents` reflects the many-to-many `documents` ↔ `boreholes` relationship (see ADR-0013) — zero, one, or many entries.

`role` is `original` for the one document the borehole was extracted from (at most one per borehole) and `additional` for any further information file (ADR-0028). The original comes first, then the rest by file name.

### Response `404 Not Found`

Returned if no borehole with that `id` exists, including ids that are not valid UUIDs:

```json
{ "errors": { "detail": "Not Found" } }
```

---

## `POST /api/boreholes`

Creates a borehole with its layers, optionally linked to an existing document (ADR-0031).

```json
{
  "borehole": {
    "name": "B 1/59 Schönberg",
    "x": 9.177, "y": 48.776, "epsg": 4326,
    "total_depth_m": 18.3,
    "purpose": "...", "place": "...", "client": "..."
  },
  "layers": [
    { "depth_from_m": 0.0, "depth_to_m": 3.5, "stratigraphy": "...", "petrography": "...", "color": "..." }
  ],
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

- `"x"`/`"y"`/`"epsg"` are reprojected to WGS84 via `ST_Transform` (ADR-0002) — omit all three (or send `"location"` directly) if coordinates aren't known yet.
- `layers[].position` defaults to the 1-based list order if not given.
- `document_id` is optional; if given, the borehole is attached as that document's `"original"` (ADR-0028, at most one per borehole).
- Everything runs in one transaction — any failure leaves nothing half-created.

### Response `201 Created`

Same shape as [`GET /api/boreholes/:id`](#get-apiboreholesid).

### Response `422 Unprocessable Entity`

Changeset validation failure (e.g. missing `name`, `depth_to_m` not greater than `depth_from_m`):

```json
{ "errors": { "depth_to_m": ["must be greater than depth_from_m"] } }
```

### Response `400 Bad Request`

Returned if `document_id` doesn't reference an existing document:

```json
{ "errors": { "detail": "document_id does not reference an existing document" } }
```

```bash
curl -X POST "http://localhost:4000/api/boreholes" \
  -H "Content-Type: application/json" \
  -d '{"borehole": {"name": "Test BH", "x": 9.177, "y": 48.776, "epsg": 4326}, "layers": []}'
```

---

## `GET /api/boreholes/search`

Ranked free-text search. Takes the same parameters as `GET /api/boreholes` (with `q` defaulting to the empty string, matching everything) and returns the same shape, plus on each feature:

| Field | Description |
|---|---|
| `score` | Relevance, higher is better: name 10, external id 8, place 5, purpose 3, client 3, plus 1 per matching layer. |
| `snippet` | Description of the first matching layer (petrography, else raw text, else stratigraphy), or `null` if only borehole fields matched. |

`q` is a case-insensitive substring match (`%` and `_` are taken literally) against `name`, `external_id`, `place`, `purpose`, `client`, and each layer's `stratigraphy`, `petrography`, `color` and `raw_text`. A borehole matching through several layers is returned once.

```bash
curl "http://localhost:4000/api/boreholes/search?q=gipskeuper&limit=10"
```

---

## `POST /api/documents`

Uploads a raw document (ADR-0033). `multipart/form-data` with the field `file` (`.pdf .png .jpg .jpeg .tif .tiff .docx`, up to 100 MB). The file is stored and the document inserted with `status: "pending"` — uploading no longer starts processing by itself (ADR-0035); call [`POST /api/pipeline_runs`](#post-apipipeline_runs) separately once you have a `config` to submit.

`202` with `{ "data": <document> }` (same fields as in a borehole's `documents`), `status` always `pending`. `400` (`{ "errors": { "detail": "..." } }`) if `file` is missing or has an unsupported type.

## `GET /api/documents/:id`

Metadata of a single document, for the document viewer page. Same fields as the entries in a borehole's `documents` (never `storage_path` or `raw_extraction`), plus the boreholes it is linked to, ordered by name.

```json
{
  "data": {
    "id": "c7a2...",
    "original_filename": "B1-59_Schichtenverzeichnis.pdf",
    "mime_type": "application/pdf",
    "source_country": "Germany",
    "status": "pending",
    "page_count": 3,
    "size_bytes": 1269760,
    "has_file": true,
    "boreholes": [{ "id": "5f1e...", "name": "B1/59" }]
  }
}
```

`404` (`{ "errors": { "detail": "Not Found" } }`) if the document does not exist or the id is not a UUID. The file itself is at [`GET /api/documents/:id/file`](#get-apidocumentsidfile).

---

## `GET /api/documents/:id/file`

The stored source file of a document, for viewing in the application (ADR-0026). Works for any
document id, not just the one from the end user's initial upload — including the split-out
per-borehole PDFs the pipeline itself uploads mid-run via `POST /api/documents` (ADR-0034). This
is how the pipeline fetches every file it needs, keyed by `document_id`; the `pipeline_runs`
webhook below never pushes file bytes.

| Param | Description |
|---|---|
| `download` | `1` or `true`: `Content-Disposition: attachment` (save) instead of `inline` (show in the browser). |

- `200` with the file, `Content-Type` from the document's `mime_type`, `Cache-Control: private, no-store`.
- `404` (`{ "errors": { "detail": "Not Found" } }`) if the document does not exist, the id is not a UUID, or no file is stored for it (`has_file: false`, e.g. generated mock documents).

```bash
curl -OJ "http://localhost:4000/api/documents/c7a2.../file?download=1"
```

---

## Pipeline runs (`pipeline_runs` / `exec_stages` / `reports`)

Debug/internal only (never consumed by `web/`'s public pages, except for status/polling fields on `pipeline_runs`). The `claude_test/` pipeline runs `01_filter` → `02_split` → `03_extract` → `04_transform` on a document, reporting each step to `exec_stages` and a final `report`, then `POST /api/boreholes` per extracted borehole (unchanged, see above).

### `POST /api/pipeline_runs`

Creates a pipeline run for a document and submits it to the pipeline (ADR-0035). The frontend calls this once it has a `config` to submit — uploading (`POST /api/documents`) no longer does this by itself.

Submission POSTs a small JSON body (`document_id`, `pipeline_id`, `config`) to `PIPELINE_URL` — no
file bytes. The pipeline fetches the document's file itself via
[`GET /api/documents/:id/file`](#get-apidocumentsidfile), the same way it fetches any split-out
per-borehole PDF it uploads mid-run.

```json
{
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "config": { "extract": "sonnet", "transform": "opus" }
}
```

| Field | Description |
|---|---|
| `document_id` | UUID of an existing document (from `POST /api/documents`). |
| `config` | Free-form map of per-stage model/effort choices, stored as-is and sent to the pipeline unchanged. |

Submission happens synchronously in this request: the response's `status` reflects whether the pipeline could be reached (`running`) or not (`new` if no `PIPELINE_URL` is configured, `failed` if the pipeline refused the request or couldn't be reached).

`201`:

```json
{
  "data": {
    "id": "6b1e...",
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "running",
    "config": { "extract": "sonnet", "transform": "opus" },
    "inserted_at": "2026-10-17T18:00:00Z",
    "updated_at": "2026-10-17T18:00:00Z"
  }
}
```

`422` (`{ "errors": { "detail": "..." } }`) if `document_id` is missing or invalid. `400` if `document_id` doesn't reference an existing document.

```bash
curl -X POST "http://localhost:4000/api/pipeline_runs" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "config": {"extract": "sonnet"}}'
```

### `GET /api/pipeline_runs/:id`

The run plus its `exec_stages` (newest first) and `report` (`null` until the pipeline has posted one). Poll this to show live progress.

```json
{
  "data": {
    "id": "6b1e...",
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "running",
    "config": { "extract": "sonnet" },
    "inserted_at": "2026-10-17T18:00:00Z",
    "updated_at": "2026-10-17T18:00:05Z",
    "exec_stages": [
      {
        "id": "...",
        "type": "extract",
        "position": 1,
        "data": { "...": "the step's JSON file as-is" },
        "document_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        "inserted_at": "..."
      }
    ],
    "report": { "id": "...", "run_id": "6b1e...", "data": { "...": "report.json as-is" }, "inserted_at": "..." }
  }
}
```

`404` (`{ "errors": { "detail": "Not Found" } }`) if the run does not exist or the id is not a UUID.

```bash
curl "http://localhost:4000/api/pipeline_runs/6b1e..."
```

### `PUT /api/pipeline_runs/:id/status`

Called by the pipeline itself when the whole run finishes. Body `{ "status": "completed" }` or `{ "status": "failed" }`. Returns the same shape as `GET /api/pipeline_runs/:id` (run + `exec_stages` + `report`).

`200` with `{ "data": <pipeline_run, with exec_stages and report> }`. `422` if `status` is not one of `new`/`running`/`completed`/`failed`. `404` if the run does not exist.

```bash
curl -X PUT "http://localhost:4000/api/pipeline_runs/6b1e.../status" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

### `POST /api/exec_stages`

Records one step execution. Append-only — rerunning a step adds a new row rather than replacing the previous one, so every attempt stays comparable.

```json
{
  "type": "extract",
  "run_id": "20261017-180433",
  "position": 1,
  "data": { "...": "the step's JSON file as-is, e.g. the raw 03_extract output" },
  "document_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
}
```

| Field | Description |
|---|---|
| `type` | `filter`, `split`, `extract` or `transform`. |
| `run_id` | Shared id string grouping every stage (and the `report`) of one pipeline run — this is the `pipeline_runs` row's `id` when the run was started via `POST /api/pipeline_runs`. |
| `position` | Borehole index within the run (1, 2, …) for `extract`/`transform`; omit/`null` for the whole-document `filter`/`split` steps. |
| `data` | Free-form JSON, the step's output file as-is. |
| `document_ids` | At least one document UUID this stage's output belongs to — the original source document, and/or (for `extract`/`transform`) the split-out per-borehole PDF once that is itself a tracked document. Creates the `stage_document_links` rows. |

`201` with `{ "data": <exec_stage, plus "document_ids"> }`. `422` if `type` is invalid or `data`/`document_ids` is missing. `400` if any `document_ids` entry doesn't reference an existing document.

### `GET /api/documents/:document_id/exec_stages`

Every stage execution linked to a document, newest first (a document can have several — append-only history). Optional `?type=` / `?run_id=` filters.

```json
{ "data": [ { "id": "...", "type": "extract", "run_id": "20261017-180433", "position": 1, "data": {}, "inserted_at": "..." } ] }
```

`404` if the document doesn't exist.

### `POST /api/reports`

Records one pipeline run's `report.json` (per-step model/time/token/cost stats).

```json
{
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "run_id": "20261017-180433",
  "data": { "...": "report.json as-is" }
}
```

`201` with `{ "data": <report> }`. `422` if a required field is missing. `400` if `document_id` doesn't reference an existing document.

---

## Route ordering note

`/api/boreholes/search` is registered before `/api/boreholes/:id` in the router — required so Phoenix doesn't match the literal path segment `"search"` as an `:id`.
