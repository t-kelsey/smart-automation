---
id: ADR-0036
date: 2026-10-17
author: claude
title: Pipeline list and detail pages with placeholder data
---

# ADR-0036 – Pipeline list and detail pages with placeholder data

## Context

Each uploaded document gets its own extraction pipeline (ADR-0033, ADR-0035). Users need to see which pipelines exist, how far they are and what failed. The API records every step execution as `exec_stages` (`filter | split | extract | transform`, one row per borehole `position` for the last two, grouped by `run_id`) and one `reports` row per run (ADR-0034, `GET /api/documents/:document_id/exec_stages`), but has no list of runs, and the pipeline is not wired to the new start flow end to end yet.

## Decision

- Two pages modelled on GitLab's pipeline UI:
  - `/pipeline`: tabs (All / Running / Finished with counts), a filename filter, and a table with Status (badge, duration, relative time), Pipeline (filename link, short id, chips), Created by, Stages (connected status circles) and a retry button.
  - `/pipeline/[id]`: tabs "Pipeline" and "Jobs (n)". The "Pipeline" tab is a flow graph with one card per stage (Filter pages, Split boreholes, Extract, Transform, Store), the stage's jobs inside, and under each stage title the job count and a status breakdown ("3 jobs · 2 passed · 1 running"). The "Jobs" tab lists all jobs with stage, model and duration.
- A pipeline's id is its document's id. Jobs are one per 10-page chunk (filter), one for the split, and one per borehole (extract, transform, store).
- Stage and pipeline status are derived from job statuses (`statusOf`: failed > running > pending > success; all skipped = skipped). Job statuses are `pending | running | success | failed | skipped`.
- Data follows ADR-0009: UI → `PipelineService` → `PipelineRepository`. The only implementation is `MockPipelineRepository` (deterministic fake runs covering every status), wired in `createServices`. This deliberately deviates from ADR-0029 (all data from the API) until the API exposes pipeline runs.
- Retry buttons and the "Created by" column are placeholders (a toast and a fixed user).

## Pros

- The pages and the domain model can be reviewed and refined without waiting for the backend.
- Replacing the mock is one line in `createServices`.

## Cons

- The pages show fake data; the "Start extraction" button does not create these pipelines yet.
- The job granularity is a guess; the real source (`exec_stages`) has one row per step and borehole, with no page-chunk jobs and no explicit running/failed status per job.

## Alternatives

- Build the pages on `exec_stages` and `reports` directly: needs a list endpoint and a status per stage in the API first.

## Consequences

- A real `ApiPipelineRepository` has to map `exec_stages` and `reports` to stages and jobs, and the API needs a way to list pipelines.

## References

- ADR-0009, ADR-0029, ADR-0033, ADR-0034, ADR-0035
