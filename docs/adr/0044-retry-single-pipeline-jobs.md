---
id: ADR-0044
date: 2026-10-18
author: ku
title: Retry single extract/transform jobs inside their run
---

# ADR-0044 – Retry single extract/transform jobs inside their run

## Context

Retrying a pipeline (ADR-0039) submits the document again as a new run, so one failed borehole
(a model timeout, a schema rejection, a DIN 4023 miss) costs the filter, split and every other
borehole's extract and transform again. The inputs of a single borehole job already exist: the
split-out PDF (a document) and the extraction result (stored in the extract `exec_stages` row).

## Decision

- `POST /api/exec_stages/:id/retry` redoes one **failed or stopped extract or transform** job of a
  **finished** run. The API reopens the run as `running` (clearing its error) and calls the
  pipeline's `POST /runs/:pipeline_id/retry` (`document_id`, `stage`, `position`, `config`); if the
  pipeline cannot be reached the run gets its previous state back.
- The pipeline records the attempt as a **new exec_stage row** (ADR-0034: reruns add rows). The old
  row stays as history; the newest row of a (type, position) is the job's current state.
- Retrying extract continues with transform for that borehole. Retrying transform reuses the stored
  extraction result and needs no PDF.
- When it is done the pipeline sets the run to `completed` only if the newest extract/transform row
  of every borehole succeeded, otherwise `failed` listing the jobs that did not.
- Only jobs that have not succeeded are retriable, so a retry never stores a second borehole for
  the same position. Filter and split jobs are not retriable on their own: everything downstream
  depends on them, so retrying the pipeline is the right tool.
- A job can only be retried while the run is not active and only once (an already retried job is
  refused with 409). The retry is queued like a run, so `POST /runs/:id/stop` cancels it too.
- Web: a retry button per failed/stopped job on `/pipeline/[id]` and on `/jobs/[id]`.

## Pros

- Costs only the failed borehole instead of the whole document.
- No new tables or statuses; reuses the exec_stage history and the run lifecycle.

## Cons

- A finished run goes back to `running`, so its `finished_at`/duration reflect only the last attempt.
- The run's report (per-step usage) covers the first attempt only; the retry's usage is on its job.
- `exec_stages.inserted_at` has second resolution, so "newest row" assumes attempts are seconds apart.

## Alternatives

- A new run per retried job: loses the link to the earlier stages and splits one document's
  boreholes over several runs.
- Allow retrying successful jobs: would need a borehole replace/delete, not available.

## Consequences

- The pipeline service gets a second queued job type, handled by the same worker.

## References

- ADR-0034, ADR-0039, ADR-0040
