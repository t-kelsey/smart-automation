---
id: ADR-0005
date: 2026-10-16
author: Tyler Kelsey
title: Store provenance and unmapped data (raw jsonb) with every borehole
---

# ADR-0005 – Store provenance and unmapped data (raw jsonb) with every borehole

## Context

Extraction will make mistakes, especially while OCR is unsolved (ADR-0001). Reviewers need to check a value against the source document. Source documents also hold information that the standard format has no field for.

## Decision

Every borehole record carries:

- **Provenance**: source file name, page numbers and a confidence or quality flag (including the missing-field flags from ADR-0004).
- **Raw data**: any extracted information that doesn't map to a format field, stored in a `raw jsonb` column on the borehole table.

## Pros

- The web UI can show where a value came from, which makes demo review possible.
- A wrong or missing field mapping loses no data; it can be remapped later from `raw`.

## Cons

- The `raw` column has no schema, so it can become a dumping ground.
- Records get somewhat larger.

## Alternatives

- Store only the mapped fields: simpler, but values can't be traced and unmapped data is lost.
- Store the full extracted text: larger, and harder to use than structured leftovers.

## Consequences

- The API schema needs `source_file`, `source_pages`, `confidence`/flags and `raw jsonb` columns.

## References

- ADR-0001, ADR-0004
