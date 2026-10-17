---
id: ADR-0035
date: 2026-10-17
author: claude
title: pipeline_runs — explicit per-document pipeline submission with run config
---

# ADR-0035 – `pipeline_runs`: explicit per-document pipeline submission with run config

> **Amended**: the webhook call described below originally pushed the document's file as
> `multipart/form-data`, mirroring ADR-0033's `submit/1`. It now posts a file-free JSON body
> instead — see the amended Decision bullet and Consequences below.

## Context

ADR-0033 had `POST /api/documents` auto-trigger the extraction pipeline in the background as soon
as a file was stored, with no way for the user to influence how it runs. `claude_test/` (ADR-0034)
calls `claude -p` per stage (`filter`/`split`/`extract`/`transform`); different stages can use
different Claude models/effort levels, and the hackathon wants the frontend to offer a dialog
where the user picks those per stage before anything runs. Auto-triggering on upload leaves no
place to inject that choice, and conflates "a file was stored" with "a pipeline run was started".

## Decision

Split upload and pipeline submission into two explicit steps:

- `POST /api/documents` (unchanged endpoint, changed behavior) only stores the file and inserts
  the `documents` row (`status: "pending"`). It no longer calls `Api.Pipeline.submit_async/1` —
  that function and its private `submit_and_track/1` helper are dead code and removed.
- A new `pipeline_runs` table/schema (`Api.Boreholes.PipelineRun`) records one submission attempt:
  `document_id` (FK), `status` (`"new"` → `"running"` → `"completed"`/`"failed"`), `config` (jsonb,
  the frontend's free-form per-stage model/effort map, stored as-is).
- `POST /api/pipeline_runs` (`{document_id, config}`) creates the row (`"new"`) and, in the same
  request, synchronously calls `Api.Pipeline.submit_pipeline_run/1`: this POSTs a small JSON body
  — `document_id`, `pipeline_id` (the pipeline run's `id`) and `config` — to `PIPELINE_URL`, with no
  file bytes. The pipeline fetches the document's file itself via `GET /api/documents/:id/file`,
  the same mechanism it already uses for the split-out per-borehole PDFs it uploads mid-run
  through `POST /api/documents` (ADR-0034) — one consistent way to fetch any document's file by
  id instead of a special-cased push for the initial trigger. Submission moves the run to
  `"running"` on success or `"failed"` if the pipeline can't be reached. No `PIPELINE_URL`
  configured is a no-op, same as ADR-0033's old auto-trigger behavior — the run stays `"new"`.
- `GET /api/pipeline_runs/:id` returns the run plus its `exec_stages` (ADR-0034, filtered by
  `run_id`) and `report` (ADR-0034, `nil` until posted), for the frontend to poll live progress.
  `PUT /api/pipeline_runs/:id/status` is called by the pipeline itself when the whole run
  finishes (`"completed"`/`"failed"`) and returns the same shape for consistency.
- `exec_stages`/`stage_document_links`/`reports` (ADR-0034) are unchanged — the pipeline still
  writes to them as it runs; `pipeline_runs` only adds the submission/status-polling layer on top.

## Pros

- The model/effort dialog has somewhere to put its output before anything runs.
- `pipeline_runs.status` gives the frontend one row to poll instead of inferring progress from
  `documents.status` (which only ever meant "this document's extraction", not "this specific run
  with this specific config").
- Reuses ADR-0034's tracking tables as-is; the webhook payload stays small regardless of file
  size since no file bytes are ever pushed.

## Cons

- `documents.status` and `pipeline_runs.status` can now disagree (e.g. a run completes but
  nothing updates the document) — nothing wires a `pipeline_runs` completion back to
  `document.status` yet; left as an open question for a follow-up.
- Re-submitting the same document creates a new `pipeline_runs` row rather than reusing one —
  acceptable for the hackathon, matches ADR-0033's "re-upload creates a second document" trade-off.
- One more table/round trip for what ADR-0033 did in a single request.

## Alternatives

- Keep auto-trigger and pass `config` as upload query params/body fields: rejected, conflates
  upload (can happen without knowing the config yet) with submission (needs the config), and
  there would be nowhere to represent "uploaded but not yet submitted".
- Store `config` on `documents` directly instead of a new table: rejected, a document can be
  resubmitted with different config without being re-uploaded, so config belongs to the run, not
  the document.

## Consequences

- `docs/api-reference.md`'s intro and the exec_stages/reports section are updated to describe the
  new two-step flow and drop the "draft, not implemented" wording for exec_stages/reports.
- `docs/elixir-backend-borehole-pipeline.md`'s "Pipeline Stage Tracking" section is updated to
  describe the current flow instead of ADR-0030's superseded one.
- `Api.Pipeline.submit/1` (ADR-0033's per-document, multipart-with-file submit function) had no
  remaining call sites once `pipeline_runs` became the only submission path, so it was removed
  rather than left as dead code; its test was rewritten to assert `submit_pipeline_run/1`'s
  JSON body and running/failed status transitions directly against the stubbed pipeline instead.
- `docs/api-reference.md` and `docs/elixir-backend-borehole-pipeline.md` are corrected wherever
  they described or implied the webhook pushes the file; `GET /api/documents/:id/file` is called
  out as usable for any document id, original or split-out, since the pipeline now relies on it
  generically rather than only for files the API itself pushed.

## References

- ADR-0014, ADR-0033, ADR-0034
