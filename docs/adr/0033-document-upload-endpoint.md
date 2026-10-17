---
id: ADR-0033
date: 2026-10-17
author: claude
title: Document upload endpoint that triggers the extraction pipeline
---

# ADR-0033 – Document upload endpoint that triggers the extraction pipeline

## Context

Documents only existed after copying files into `api/priv/uploads/` and running `mix documents.backfill` (ADR-0014, ADR-0032). The web app had no way to add a raw log, and `bem` was a CLI without an HTTP entry point.

## Decision

- `POST /api/documents` (multipart field `file`, max 100 MB; `.pdf .png .jpg .jpeg .tif .tiff .docx`) stores the file directly in the managed storage as `<id><ext>` and inserts a `documents` row (status `pending`). It answers `202` with the document. Unlike the backfill task, it skips `priv/uploads/` so nothing needs moving.
- If `PIPELINE_URL` is set, `Api.Pipeline` sends the file in the background (`Task.Supervisor`, `Req`) as multipart (`document_id`, `file` named `<id><ext>`) to that URL and sets the status to `processing`; a refused or unreachable pipeline sets `failed`. Without `PIPELINE_URL` the upload is only stored.
- `bem-serve` (`bem/src/bem/server.py`, FastAPI) is that endpoint: `POST /process` queues the file and answers `202`; one worker runs the usual pipeline (`process_file`) and reports through the existing endpoints. The file is named after its document ID, so stage tracking and the borehole link work as for backfilled files. The worker finishes with the new `PUT /api/documents/:id/status` (`extracted` or `failed`).
- The file is sent over HTTP, so API and pipeline share no volume.
- Web: sidebar link "Upload" and `/upload` page (UI → `UploadService` → `ApiUploadRepository`, ADR-0009).

## Pros

- The whole flow works from the browser; the pipeline can run anywhere the API can reach.
- Nothing about the pipeline changed apart from the entry point.

## Cons

- The queue is in memory in `bem-serve`: a restart loses queued files (their documents stay `processing`).
- No authentication and no virus scanning (hackathon prototype).
- Re-uploading the same file creates a second document and, on success, duplicate boreholes (ADR-0032).

## Alternatives

- Shared volume and a path sent to the pipeline: simpler payload, but couples the deployments.
- Run the pipeline inside the API process: Python/ML stack does not belong in Elixir.

## Consequences

- `PIPELINE_URL` (API) configures the target; `docker compose --profile bem up` starts `pipeline`.
- `req` is a new API dependency.

## References

- ADR-0014, ADR-0030, ADR-0032, `bem/API_INTEGRATION.md`
