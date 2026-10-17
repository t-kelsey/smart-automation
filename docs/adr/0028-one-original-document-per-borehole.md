---
id: ADR-0028
date: 2026-10-17
author: Kasimir Uihlein
title: Each borehole has exactly one original document and any number of additional files
---

# ADR-0028 – Each borehole has exactly one original document and any number of additional files

## Context

ADR-0013 made documents and boreholes many-to-many, so a borehole can have several files. The files are not equal, though: one is the log the layers were extracted from, the others (core photos, reports, summaries) only add information. The review view (`/borehole/[id]/review`) puts the extracted cross section and layers next to the source log so a reviewer can check the extraction, so it has to know which file that is.

## Decision

- The `borehole_documents` join table gets a `role` column, `original` or `additional` (default `additional`, enforced by a check constraint).
- A partial unique index on `borehole_id` where `role = 'original'` allows at most one original document per borehole. Further files are `additional` without limit.
- The role is on the link, not on the document: one scanned report can cover several boreholes and be the original of one and an additional file of another.
- "Exactly one" is a rule for ingestion, not for the database: the pipeline, seeds and mock data attach one original with `Api.Boreholes.attach_documents/3`. A borehole without any original document stays possible (e.g. created by hand) and the review view then shows its first additional file or an empty state.
- `GET /api/boreholes/:id` returns each document with its `role`, the original first. Other endpoints are unchanged.
- The migration marks the oldest existing link of each borehole as its original.
- The web app shows the original document in the review view next to the extracted data, with a switch to the additional files. The borehole page marks the original in its document list.

## Pros

- Which file is the source of the extraction is explicit and queryable, not guessed from order or name.
- The database guarantees at most one original per borehole, even with concurrent ingestion.
- A shared document can have a different role for each borehole it covers.

## Cons

- "At least one original" is not enforced by the database.
- The migration has to guess the original for existing data (oldest link).
- No endpoint changes the role yet; it is set at ingestion.

## Alternatives

- A nullable `original_document_id` on `boreholes`: also gives at most one, but a second link table row is still needed for the additional files, and the same document could be both original and additional for one borehole.
- Role on the `documents` row: wrong for documents shared between boreholes (ADR-0013).
- Treat the first document as the original: depends on ordering and breaks silently.

## Consequences

- The ingestion pipeline (`bem/`) must say which file is the original when it links documents.
- `docs/api-reference.md` documents `role`.
- A later feature that replaces the original needs an endpoint that swaps roles in one transaction.

## References

- ADR-0013, ADR-0026
- docs/api-reference.md
