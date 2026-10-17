---
id: ADR-0031
date: 2026-10-17
author: jl
title: Synchronous borehole creation endpoint instead of the upload-and-Oban design
---

# ADR-0031 – Synchronous borehole creation endpoint instead of the upload-and-Oban design

## Context

Task 2 ("Ingestion pipeline") in `docs/elixir-backend-borehole-pipeline.md` originally specified an async design: a file-upload endpoint creates a `documents` row with `status: :pending`, and an `Oban` background job calls an external extraction service, stores the raw response, and standardises it into `boreholes`/`borehole_layers`.

In practice: there is no file-upload endpoint yet (per team decision, `bem/` currently works against documents already tracked via `mix documents.backfill`, see `bem/API_INTEGRATION.md`), and there is no external synchronous "extraction service" to poll — `bem/` runs OCR/translation/triage/extraction itself, locally, and is the one reporting results. An async job with retries makes little sense when there's nothing external to wait on or retry.

## Decision

Built `POST /api/boreholes` as a plain synchronous endpoint instead:

```json
{
  "borehole": { "name": "...", "x": 9.177, "y": 48.776, "epsg": 4326, "total_depth_m": 18.3, "...": "..." },
  "layers": [ { "depth_from_m": 0.0, "depth_to_m": 3.5, "stratigraphy": "...", "...": "..." } ],
  "document_id": "3fa85f64-..."
}
```

- `"x"`/`"y"`/`"epsg"` are accepted instead of a `"location"` directly — set via `ST_Transform(ST_SetSRID(ST_MakePoint(x, y), epsg), 4326)` (ADR-0002), so the caller never has to reproject coordinates itself.
- `layers[].position` defaults to the 1-based list order if not given.
- `document_id`, if given, attaches the new borehole to that document as its `"original"` (ADR-0028), via the existing `attach_documents/3` — not new linking logic.
- Insert borehole → set location → insert layers → attach document all run in one `Repo.transaction`; any failure (changeset error, unknown `document_id`) rolls back the whole thing.
- `201` with the same shape as `GET /api/boreholes/:id` on success; `422` with field errors for changeset failures; `400` if `document_id` doesn't reference an existing document.

## Pros

- No background-job infrastructure needed for the hackathon scope — one less dependency (`Oban` stays an unused suggestion in `mix.exs` for now).
- `bem/` gets a definitive success/failure and the created id in the same request it made, which it then reports back to the API — simpler than correlating an async job's eventual outcome back to a specific section.
- Reuses `attach_documents/3` (and its "at most one original document" constraint, ADR-0028) instead of inventing new linking logic.

## Cons

- A slow or failing request blocks the caller; no automatic retry (unlike Oban).
- Not idempotent — calling it twice creates two boreholes. Acceptable here because `bem/` calls it at most once per triage section, right after reporting that section's `extraction_result`.

## Alternatives

- The original upload-endpoint-plus-Oban design — kept as a documented alternative, not built: revisit if a real external OCR/extraction service (one actually worth retrying against) gets introduced later, or if a file-upload endpoint is needed (`bem/` currently doesn't need one, see `bem/API_INTEGRATION.md`).

## Consequences

- Task 2 in `docs/elixir-backend-borehole-pipeline.md` is superseded by this ADR for the "create the borehole" step; the upload endpoint and `Oban` job remain unbuilt and not currently planned.
- `docs/api-reference.md` documents this endpoint alongside the existing read endpoints.

## References

- ADR-0002, ADR-0012, ADR-0013, ADR-0023, ADR-0028
- docs/elixir-backend-borehole-pipeline.md
- docs/api-reference.md
- bem/API_INTEGRATION.md
