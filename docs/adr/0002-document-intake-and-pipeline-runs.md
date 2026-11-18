---
id: ADR-0002
date: 2026-11-18
author: Tyler Kelsey
title: Document intake, pipeline runs, stage tracking and confidential documents
---

# ADR-0002 – Document intake, pipeline runs, stage tracking and confidential documents

## Context

Source documents are confidential and must never be committed, published or sent to external services. Extraction runs as a multi-step LLM pipeline (`bem/`: `filter` → `split` → `extract` → `transform`) that can take minutes and cost money, so users must choose models per step, see progress, retry single failures and stop runs. Reviewers also need to see a source scan next to its extracted data.

## Decision

**Storage layout.** `api/priv/uploads/` is a staging inbox (not yet tracked); `api/priv/storage/` is the managed store with files named `<document_id><ext>`, flat. Both are gitignored except `.gitkeep` and sit outside `priv/static`. `mix documents.backfill` moves manually dropped files from the inbox into the store and creates their rows.

**Upload.** `POST /api/documents` (multipart `file`, max 100 MB; `.pdf .png .jpg .jpeg .tif .tiff .docx`) stores the file directly in the store and inserts a `documents` row with `status: "pending"`. It triggers nothing.

**Serving files.** `GET /api/documents/:id/file` serves the file inline, or as an attachment with `?download=1`, with `Cache-Control: private, no-store` and `X-Robots-Tag: noindex`. Only plain file names directly in the store are served. `storage_path`, `raw_extraction` and any file path never appear in JSON; the detail endpoint only adds `has_file`.

**Run submission.** The frontend calls `POST /api/pipeline_runs` with `{document_id, config}`. The API creates a run (`new`) and synchronously posts a file-free JSON body (`document_id`, `pipeline_id` = run id, `config`) to `PIPELINE_URL`'s `POST /execute`. Accepted → `running`; unreachable or refused → `failed`; `PIPELINE_URL` unset → stays `new`. The pipeline downloads the file itself via `GET /api/documents/:id/file`.

**Run config.** One `{model, effort}` object per step, stored as-is in `pipeline_runs.config`. Defaults: `filter` haiku/high, `split` haiku/medium, `extract` sonnet/high, `transform` haiku/high. The UI offers haiku, sonnet and opus with low, medium and high.

**Run lifecycle.** `pipeline_runs.status` is `new`, `running`, `completed`, `failed` or `stopped`, with `started_at`, `finished_at`, `current_stage` and `error`. The pipeline reports the outcome with `PUT /api/pipeline_runs/:id/status`. A finished run keeps its status: a later different status gets `409`, so a user's stop wins over a late `failed`. The run completes only if the newest extract and transform row of every borehole succeeded.

**Stop.** `POST /api/pipeline_runs/:id/stop` sets `stopped` and calls the pipeline's `POST /runs/:id/stop`. The pipeline checks its stop flag before every stage, borehole and model request. In-flight model calls finish first; a queued run is skipped. Ending a run marks its still `new` or `running` stages `stopped`.

**Stage tracking.** `exec_stages` (append-only) has `type` (`filter | split | extract | transform`), `run_id` (the pipeline id), `position` (borehole index; null for filter and split), `status` (`new | running | success | failed | stopped`), timing, `error`, `model`, `effort`, `usage` jsonb and `data` jsonb. The pipeline creates stages as `new` and updates them with `PUT /api/exec_stages/:id`; finished stages cannot change. `stage_document_links` connects a stage to documents: filter links the original, extract and transform link the original and the split-out borehole PDF. `reports` holds one `report.json` per run, posted at the end of a normal return.

**Retry.** `POST /api/exec_stages/:id/retry` redoes one failed or stopped `extract` or `transform` job of a finished run. The run reopens as `running` and the pipeline's `POST /runs/:id/retry` is called; if the pipeline is unreachable the previous state is restored. The retry is a new stage row; the newest row per (type, position) is the job's state. Each job can be retried once (`409` otherwise). `transform` reuses the stored extraction result. Filter and split are not retriable; rerun the pipeline instead.

**Run read API.** `GET /api/pipeline_runs/:id` returns the run, its stages, the report (or null), `stage_counts` and `duration_ms`. `GET /api/pipeline_runs` lists runs with `document_filename`.

**Web flow.** `/upload` stages files in memory (a reload empties the queue). `/upload/config` sets the config, uploads each file, and submits a run per file. A file leaves the queue once its run is `running`; files that failed stay queued with their document id, so a retry does not upload twice. `/pipeline` and `/pipeline/[id]` poll every 3 s while a run is pending or running. Stage and job status is shown from the rows; a missing row means pending.

**Confidentiality.** Source documents may be shown inside the application, but must never be published, committed or sent to external services. There is no authentication yet, so the API must stay on a local machine or trusted network. Mock documents all point to one example PDF (`mock_borehole_log_example.pdf`) that is installed on seed or when mock boreholes are generated; deleting a mock document leaves the file in place.

**Legacy.** `PUT /api/documents/:id/status` still exists but no part of the current flow calls it. A run's completion does not update `documents.status`; the two can disagree.

## Pros

- Each run keeps its own config, history and report, so reruns and prompt changes can be compared.
- The user sees the real state of every job, including the reason for a failure and the cost per borehole.
- Failed boreholes can be retried without paying for the whole document again.
- A wrong or runaway run can be stopped without restarting the pipeline.
- The webhook payload stays small; file bytes travel only through the document endpoint.
- Documents are served by id only, so disk paths stay internal.

## Cons

- Many round trips: about two to three per stage and borehole.
- A stop is cooperative; a running `claude -p` call still costs money until it returns.
- The in-browser queue is lost on reload.
- `documents.status` and `pipeline_runs.status` can disagree.
- Anyone who can reach the API can read the documents; the rule against publishing relies on the people using the application.
- The list endpoint has no stage summary, so the overview loads each run in full.
- Re-submitting or re-uploading the same file creates duplicate documents and boreholes.

## Alternatives

- **Auto-start the pipeline on upload:** rejected; it leaves no place for the user's model and effort choice.
- **Config on the document:** rejected; a document can be rerun with a different config.
- **Shared volume and file path for the pipeline:** rejected; it couples the deployments. Sending bytes in the webhook was dropped in favour of the document endpoint.
- **Run the pipeline inside the API:** rejected; the Python and LLM stack does not belong in Elixir.
- **Derive stage status from row presence:** rejected; it cannot tell running from failed or stopped.
- **One status per run with a stage pointer:** rejected; loses per-borehole status for stages that run in parallel.
- **Kill the `claude` subprocess on stop:** not done yet; needs shared process handles across threads.
- **Retry a whole new run per failed job:** rejected; splits one document's boreholes over several runs.
- **Hide documents from the application (backend only):** rejected; reviewers need the scan next to the extraction. Authentication is the prerequisite for any wider exposure.

## Consequences

- The pipeline (`bem/`) must use `pipeline_id` as its `run_id`, set EPSG codes, and say which file is the original when linking documents.
- A borehole whose petrography cannot be mapped to DIN 4023 is not posted, and its run is marked failed (see ADR-0004).
- Before the API is reachable by anyone outside the team, authentication is required.
- Future amendments to this flow should be a new ADR rather than edits that make this one hard to follow.

## References

- `bem/README.md`, `bem/pipeline/server.py`, `bem/pipeline/output.py`
- `api/lib/api/pipeline.ex`, `api/lib/api/boreholes.ex`
- `api/lib/api_web/controllers/` (document, pipeline_run, exec_stage, report)
- `docs/api-reference.md` ("Pipeline runs")
- `api/priv/repo/assets/` (example document)
