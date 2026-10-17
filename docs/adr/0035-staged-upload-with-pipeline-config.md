---
id: ADR-0035
date: 2026-10-17
author: claude
title: Stage uploads in the browser and choose models and effort before uploading
---

# ADR-0035 – Stage uploads in the browser and choose models and effort before uploading

## Context

Users need to drop wrong files again and to pick which AI models and how much effort the pipeline uses. ADR-0033's upload endpoint sends every file to the pipeline as soon as it is uploaded, so the choices have to be made before anything is uploaded.

## Decision

- No API change. Files are staged in the browser and uploaded only at the end of the flow.
- `/upload` collects files (drop or choose) into a client-side queue (`upload-queue.svelte.ts`). Removing one with ✕ just drops it from the queue. A Continue button above the list goes to `/upload/config`.
- `/upload/config` shows the settings card (model and effort per pipeline step, Skeleton `SegmentedControl`s) above the file list. "Start extraction" uploads every queued file with `POST /api/documents` (ADR-0033), which hands each to the pipeline. Files that fail stay in the queue; when all succeed the app goes to `/pipeline`.
- The chosen config is not sent anywhere yet: `POST /api/documents` takes no config. The pipeline itself now accepts one (`POST /execute`, JSON body with `document_id` and `config`), so the missing piece is the API calling it.
- The queue lives in memory, so a page reload empties it. Nothing is stored on the server before the upload.

### Run config format

The UI's config has the shape of the `config` field of the pipeline's `POST /execute` (`bem/pipeline/server.py`, `bem/pipeline/config.py`): one `{model, effort}` object per step, with these defaults (`createDefaultPipelineConfig`):

```json
{
  "filter":    { "model": "haiku",  "effort": "high" },
  "split":     { "model": "haiku",  "effort": "medium" },
  "extract":   { "model": "sonnet", "effort": "high" },
  "transform": { "model": "haiku",  "effort": "high" }
}
```

| Step (key) | What it does |
| --- | --- |
| `filter` | keeps only the borehole log pages |
| `split` | one file per borehole |
| `extract` | reads depths, lithology, stratigraphy |
| `transform` | standardises the result for the database |

The pipeline accepts any model and effort string (hints for its AI backend); the UI offers `haiku`, `sonnet` and `opus` with `low`, `medium` and `high`, although `claude_cli` also knows `xhigh` and `max`.

## Pros

- Removing a file needs no endpoint and leaves no data behind.
- Nothing reaches the pipeline (or is billed) before the user confirms.
- The config UI can be reviewed before the backend can use it.

## Cons

- The chosen models and effort have no effect yet.
- A reload loses the selected files.
- Large batches are uploaded sequentially from the browser.

## Alternatives

- Upload on selection and delete on removal: needs a delete endpoint, and with ADR-0033 the pipeline would already be running.
- A separate start endpoint taking the config (`POST /api/documents/start`), which was drafted and dropped.

## Consequences

- To make the config effective, the upload (or a start request) must carry it to the pipeline.

## References

- ADR-0033
