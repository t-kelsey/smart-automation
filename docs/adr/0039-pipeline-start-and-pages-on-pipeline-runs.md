---
id: ADR-0039
date: 2026-10-17
author: claude
title: Start pipelines and show pipeline pages from pipeline_runs
---

# ADR-0039 – Start pipelines and show pipeline pages from `pipeline_runs`

## Context

ADR-0035 added `pipeline_runs` (`POST /api/pipeline_runs`, `GET /api/pipeline_runs/:id`) on top of the `exec_stages` and `reports` of ADR-0034. The web app so far only staged uploads (ADR-0038) and showed mock pipelines (ADR-0036).

## Decision

- **Start:** "Start extraction" on `/upload/config` uploads each queued file (`POST /api/documents`) and submits it with `POST /api/pipeline_runs` and the chosen config (`{filter|split|extract|transform: {model, effort}}`, the shape the pipeline's `POST /execute` expects). A file leaves the queue when its run is `running`. A file that is uploaded but whose run did not start (`pending`: no `PIPELINE_URL`; `failed`) stays queued with its document id, so a retry does not upload it again. One started run opens its page, several open `/pipeline`.
- **Pages:** `/pipeline` and `/pipeline/[id]` read `pipeline_runs` through `ApiPipelineRepository`, replacing `MockPipelineRepository`. A pipeline's id is the run id. `get` loads `GET /pipeline_runs/:id` (run, `exec_stages`, report) and the document for its filename; `list` loads `GET /pipeline_runs` (which carries `document_filename`) and then each run in full for its stages.
- **Stages and jobs** (`pipeline-mapper.ts`): the four stages are the `exec_stages` types. Filter and split are one job each; extract and transform have one job per borehole, named from the split result (`data.boreholes[].label`). A stage's model, effort and wall time come from the report's steps (the config before the report exists).
- **Status:** the pipeline only reports a stage when it has finished, so what is missing is derived from the run: while `running`, the unfinished jobs of the first unfinished stage run and later stages are pending; when `failed`, those jobs failed and later stages are skipped; `new` is all pending; `completed` is all done. The run status maps to the pipeline status (`new` pending, `completed` success).
- **Live updates:** the pages poll with `invalidate('app:pipelines')` every 3 s while a pipeline is pending or running.
- **Retry:** submits the same document with the same config again (a new run). There are no per-job retries.
- The "Store" stage and the "Created by" column of the mock are gone (nothing records them).

## Pros

- The config chosen in the UI reaches the pipeline and the pages show real runs.
- Works with the existing endpoints.

## Cons

- The list endpoint has no stages or report, so `/pipeline` loads every run in full (N+1 requests) to draw the stage overview. A stage summary in the list response would remove that. The list also supports `status`, `document_id`, `limit` and `offset`, which the UI does not use yet.
- `GET /pipeline_runs/:id` only returns stages and a report whose `run_id` is the run id. The pipeline currently posts them with its own timestamp run id, so the pages show no stage results until `bem/pipeline/server.py` uses `pipeline_id` as the run id.
- Running jobs are guessed (all unfinished jobs of the active stage), and per-job durations only exist for single-job stages.
- Run status and `documents.status` can disagree (ADR-0035).

## Alternatives

- Keep the mock until all endpoints exist: the pages could not be tried against the real pipeline.
- A status per stage written by the pipeline: more accurate, but needs pipeline and API changes.

## Consequences

- Supersedes ADR-0036; the mock repository was removed.
- The run id fix in bem (use `pipeline_id` as `run_id`, as ADR-0037 describes) makes the stage results show up.

## References

- ADR-0034, ADR-0035, ADR-0036, ADR-0037 (the consolidated flow), ADR-0038
