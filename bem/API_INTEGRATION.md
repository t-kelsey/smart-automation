# API Integration: reporting pipeline results to `api/`

This is for whoever wires up `bem/`'s output once OCR → translation → triage → extraction work
end to end. It describes the HTTP contract `api/` exposes for exactly that — not a design
proposal, these endpoints exist and are tested today. Design background: `docs/elixir-backend-borehole-pipeline.md`
("Proposed Extension: Pipeline Stage Tracking") and ADR-0002/0012/0013/0014.

Base URL for local dev: `http://localhost:4000/api` (start with `cd api && mix phx.server`).

## 1. Get a `document_id` first

Every call below needs a `document_id` — the UUID of a `documents` row that already exists in
the database. There is currently **no upload endpoint**; documents are tracked by dropping files
into `api/priv/uploads/` and running `mix documents.backfill` (see the repo root `README.md`).

That task renames every file to `<document_id><ext>` inside `api/priv/storage/` (ADR-0014). So if
`bem/` reads its input files from `api/priv/storage/` directly, **the document_id is the file's
stem** — no API call needed to get it:

```python
from pathlib import Path

def document_id_from_path(path: Path) -> str:
    return path.stem  # "3fa85f64-5717-4562-b3fc-2c963f66afa6.pdf" -> "3fa85f64-..."
```

## 2. Report each stage as it finishes

All of these are **PUT**, not POST: every call is an upsert (safe to call again with the same
`document_id`/`stage`/`section_index` — it replaces the previous result, it doesn't duplicate).
None of this is ever shown in `web/` or any public response — it's debug/tracking only.

### OCR / translation result (once per document)

```
PUT /api/documents/:document_id/pipeline_stages/:stage      # stage = "ocr" | "translation"
```
```json
{
  "status": "ok",
  "output": { "markdown": "..." },
  "error": null
}
```
For `"translation"`, put whatever is useful in `output`, e.g. `{"translated_markdown": "...", "source_language": "de", "translate_errors": [...]}`. `output` is free-form JSON — nothing to agree on with `api/`, put whatever helps debugging.

### Triage sections (once per document, replaces all of them)

```
PUT /api/documents/:document_id/triage_sections
```
```json
{
  "sections": [
    { "borehole_id_guess": "BH-1", "raw_markdown": "...", "translate_errors": [] },
    { "borehole_id_guess": "BH-2", "raw_markdown": "...", "translate_errors": ["translate_error: ..."] }
  ]
}
```
`section_index` is optional per section (defaults to its 0-based position in the list) — only set it explicitly if your triage order isn't the list order.

### Extraction result (once per section)

```
PUT /api/documents/:document_id/triage_sections/:section_index/extraction_result
```
```json
{
  "status": "ok",
  "extracted_fields": { "name": "BH-1", "total_depth_m": 18.3, "layers": [...] },
  "validation_issues": {}
}
```
`extracted_fields`/`validation_issues` are free-form JSON too — put the extraction's raw candidate record here for debugging, whatever shape is convenient.

## 3. Actually create the borehole

This is the one call that matters beyond debugging — it's what makes the borehole show up on the
map in `web/`.

```
POST /api/boreholes
```
```json
{
  "borehole": {
    "name": "BH-1",
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
- Send raw `x`/`y`/`epsg` instead of already-reprojected coordinates — `api/` converts to WGS84 itself (ADR-0002). If you don't have georeferencing yet, omit all three.
- `layers[].position` is optional (defaults to 1-based list order).
- `document_id` links the new borehole to its source file (ADR-0013) — omit it to create an unlinked borehole.
- `201` + the created borehole (same shape as `GET /api/boreholes/:id`) on success. `422` with `{"errors": {...}}` per invalid field on validation failure (e.g. `depth_to_m` not greater than `depth_from_m`). `400` if `document_id` doesn't exist.

## 4. Report what happened (once per section)

```
PUT /api/documents/:document_id/triage_sections/:section_index/sink_result
```
Success:
```json
{ "target": "api", "success": true, "response_status": 201, "created_borehole_id": "<id from step 3>" }
```
Failure (step 3 returned non-2xx, or wasn't attempted):
```json
{ "target": "api", "success": false, "response_status": 422, "error": "<response body or exception text>" }
```

## Full order, per document

```
pipeline_stages/ocr  →  pipeline_stages/translation  →  triage_sections  →  for each section: extraction_result  →  POST /boreholes  →  sink_result
```

## Rules that don't change

- Never send anything from `data/` (the confidential sample dataset) to any service outside this
  repo's own `api/` — these are internal endpoints on your own machine/network, not a third party,
  so that's fine; just don't also e.g. log full document content to an external error tracker.
- All of the above is unauthenticated right now (hackathon prototype) — fine for local dev, not
  for anything deployed publicly.
