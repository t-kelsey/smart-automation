---
id: ADR-0040
date: 2026-10-17
author: ku
title: Stage and run lifecycle monitoring (status, timing, usage, stop)
---

# ADR-0040 – Stage and run lifecycle monitoring (status, timing, usage, stop)

## Context

Until now `bem/` only wrote an `exec_stages` row (ADR-0034) once a stage had finished, and
`pipeline_runs` (ADR-0035) only knew `new`/`running`/`completed`/`failed`. While a run was going,
the frontend had to guess which stage was running from which rows were missing. A failed stage
was stored as an ordinary row with `{"status": "failed", ...}` hidden in `data`. Stages that never
ran left no trace, and timing, model and token usage were only in the run's report, which is
posted at the very end and is lost when the run fails. A run could not be cancelled once it was
started, even though one run can cost several minutes of model calls.

## Decision

- **Stage lifecycle.** `exec_stages` get `status` (`new | running | success | failed | stopped`,
  default `new`), `started_at`/`finished_at` (stamped by the API on `running` and on the terminal
  statuses), `error`, `model`, `effort` and `usage` (jsonb: calls, tokens, cost, models). `data`
  becomes nullable. `PUT /api/exec_stages/:id` reports progress and can link more documents. A
  finished stage (`success`/`failed`/`stopped`) cannot change any more. Existing rows are
  migrated to `success`, or `failed` if their data said so.
- **bem reports the lifecycle as it happens.** At the start of a run it creates `filter` and
  `split` as `new`. Once split has found the boreholes, it creates `extract`/`transform` per
  borehole as `new`, linked to the original and the split-out PDF. Each stage turns `running`
  when it starts and `success`/`failed`/`stopped` when it ends, with its result, error, model,
  effort and usage. Per-borehole usage comes from a child `StepReport` that also counts towards
  the step's total. A `transform` stage only counts as `success` once its borehole is stored, and
  its `data.borehole_id` then points at it. A refused borehole (DIN 4023 or the API) fails that
  stage. In code this is a `Tracker` interface (`bem/pipeline/output.py`): the steps call
  `Recorder.start/record/record_failure`, and the server's `RunTracker` turns them into API calls.
  Tracking errors are logged and never abort the extraction.
- **Run lifecycle.** `pipeline_runs` gets `stopped`, plus `started_at`/`finished_at`,
  `current_stage` (set by the API whenever a stage of the run starts running) and `error`. `PUT
  /api/pipeline_runs/:id/status` accepts `error`. Ending a run marks its stages that are still
  `new`/`running` as `stopped`, so the stage list is complete even if bem crashed mid-run. A
  finished run keeps its status (409 on a different one), so a user's stop wins over the
  pipeline's late `failed`.
- **Stop.** `POST /api/pipeline_runs/:id/stop` sets the run to `stopped` and calls bem's `POST
  /runs/:id/stop`, derived from `PIPELINE_URL`. bem sets the run's stop event; it is checked
  before every stage, every borehole and every model request (`StepReport.raise_if_stopped`).
  Calls already in flight finish first. A run that is still queued is skipped.
- `GET /api/pipeline_runs/:id` adds `stage_counts` (stages per status) and `duration_ms` on runs
  and stages.

## Pros

- The frontend can show the true state of every job (running, failed with the reason, stopped)
  instead of deriving it, and it shows planned jobs before they start.
- Cost and duration are visible per stage and per borehole as soon as each one finishes, even
  when the run fails before its report is posted.
- A wrong or runaway run can be cancelled without restarting bem.

## Cons

- More API round trips per run: about two to three per stage and borehole instead of one.
- A stop is cooperative. A long `claude -p` call that is already running is not killed and
  still costs money until it returns.
- `run_id` stays a string that is not a foreign key, so `current_stage` is only kept for stages
  whose `run_id` is a `pipeline_runs.id`.

## Alternatives

- **Derive status from row presence (as before).** This needs no schema change, but it cannot
  tell running from failed or stopped, and it cannot show planned work.
- **One status row per run with a stage pointer.** This is simpler, but it loses per-borehole
  status, timing and usage for extract/transform, which run in parallel.
- **Kill the claude subprocess on stop.** This gives a faster stop, but the process handles would
  need to be shared across the step threads. The cooperative check is enough for now.

## Consequences

- Clients of `exec_stages` must read `status` instead of treating every row as a finished
  result. `web/`'s pipeline mapper and job detail page do so (`new` → pending, `stopped` →
  skipped).
- bem's `run_pipeline` takes a `tracker` and a `stop` event instead of the old `on_stage`
  callback.
- `mix pipeline_runs.mock` generates stages with statuses, timing and errors.
- The run report (`POST /api/reports`) is still only posted when the pipeline returns normally.

## References

- ADR-0034 (exec_stages/reports), ADR-0035 (pipeline_runs), ADR-0037 (end-to-end flow)
- `docs/api-reference.md`, "Pipeline runs" section
- `api/priv/repo/migrations/20261017213827_add_status_tracking_to_exec_stages_and_pipeline_runs.exs`
- `bem/pipeline/server.py` (`RunTracker`, `/runs/{id}/stop`), `bem/pipeline/output.py` (`Tracker`)
