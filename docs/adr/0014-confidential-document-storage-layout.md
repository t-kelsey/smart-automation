---
id: ADR-0014
date: 2026-10-17
author: jl
title: Confidential document storage layout - uploads inbox and managed storage
---

# ADR-0014 – Confidential document storage layout - uploads inbox and managed storage

> Partly superseded by ADR-0026: documents may be shown in the application through the API. The storage layout below still applies.

## Context

Source documents (borehole PDFs/scans/images) are confidential per the data-sharing terms and must never be committed to git or exposed via any public API/frontend endpoint. Some sample data was manually copied onto disk rather than going through an upload endpoint, which doesn't exist yet (see the Elixir backend task doc, Task 2).

## Decision

Two directories under `api/priv/`, both gitignored except for a `.gitkeep` placeholder so the empty folder itself is still tracked in git:

- `uploads/` — a staging inbox. Anything here is **not yet** tracked in the `documents` table.
- `storage/` — the managed store. Files live here flat (no subfolders), renamed to `<document_id><ext>`.

`mix documents.backfill` processes the inbox: for each file, it generates the `documents.id` up front, inserts the row with the future `storage_path`, then moves the file into `storage/`. If the move fails, the row is deleted again so the inbox and the `documents` table stay consistent.

## Pros

- The `<document_id><ext>` naming makes the file↔row relationship trivially derivable from the filename alone, no separate bookkeeping needed.
- The inbox/managed-store split gives a clear invariant (file in `uploads/` ⇒ not yet tracked), avoiding the earlier confusion of files existing on disk with no corresponding DB row.
- Both directories live outside `priv/static`, so Phoenix never serves them publicly.

## Cons

- Two directories to reason about instead of one.
- `mix documents.backfill` is a stop-gap for data that didn't come through the (future) upload endpoint, and needs to stay in sync with whatever that endpoint does.

## Alternatives

- Keep the original uploaded filename as the storage filename — rejected: collisions between different source files sharing a name, and the project already hit real permission/escaping issues with special characters in original filenames during manual copying.
- Store files in S3 from day one — deferred; local disk is sufficient for the hackathon, swap to an S3-compatible bucket later if persistence across deploys is needed.

## Consequences

- Once the real upload endpoint (Task 2) exists, it should write directly into `priv/storage/` with a freshly generated UUID and skip the `uploads/` inbox entirely for new uploads. `mix documents.backfill` remains useful only for manually-dropped data going forward.

## References

- docs/elixir-backend-borehole-pipeline.md
- api/lib/mix/tasks/documents.backfill.ex
