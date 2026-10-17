---
id: ADR-0013
date: 2026-10-17
author: jl
title: documents and boreholes are many-to-many, not a document_id foreign key
---

# ADR-0013 – documents and boreholes are many-to-many, not a document_id foreign key

## Context

`boreholes` was initially modelled with a `document_id` foreign key (one document → many boreholes). In practice a single scanned report can cover several boreholes, and the same borehole can be documented across multiple files (e.g. a scan plus a typed follow-up report) — a plain one-to-many doesn't fit either direction.

## Decision

Replace `boreholes.document_id` with a join table `borehole_documents` (`borehole_id`, `document_id`, unique on the pair, `on_delete: :delete_all` on both sides), modelled as `many_to_many` on both `Api.Boreholes.Borehole` and `Api.Boreholes.Document`.

## Pros

- Correctly represents the real-world many-to-many relationship without data duplication.
- A borehole's full source documentation (multiple files) is directly queryable via the association.

## Cons

- Slightly more complex to wire up than a foreign key — requires `put_assoc`/`Repo.preload` instead of just setting a column.
- One additional table and migration to maintain.

## Alternatives

- Keep the one-to-many `document_id` and duplicate a `documents` row per borehole when one file covers several — rejected, duplicates confidential file metadata and loses a single source of truth per uploaded file.

## Consequences

- The ingestion pipeline must associate boreholes with their document(s) via `put_assoc` on insert, not a simple `document_id` assignment.

## References

- docs/elixir-backend-borehole-pipeline.md
- ADR-0012
