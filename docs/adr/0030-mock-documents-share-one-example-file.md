---
id: ADR-0030
date: 2026-10-17
author: Kasimir Uihlein
title: All mock documents point at one example log file in the storage directory
---

# ADR-0030 – All mock documents point at one example log file in the storage directory

## Context

Mock and seeded documents (ADR-0025) had made-up `storage_path`s, so the document viewer (ADR-0026) showed "no file" for them. The team added a sample borehole log, `api/priv/repo/assets/borehole_log_example.pdf`.

## Decision

- `Api.MockData.install_example_file/0` copies the asset into the storage directory as `mock_borehole_log_example.pdf`. It runs when `priv/repo/seeds.exs` runs and when `mix boreholes.mock` creates at least one borehole, and never otherwise.
- Every seeded and generated document uses that `storage_path`, `application/pdf`, and the file's real size and page count. Names, countries and statuses still vary per row.
- `MOCK_BOREHOLES` (from `.env`, read by the seeds) only controls the number of boreholes; the file is installed regardless, because the hand-written examples need it too.

## Pros

- The viewer works for all mock rows with one small file; no per-row copies.

## Cons

- Mock rows are less varied: every document shows the same log, and documents of other types (image, docx) are no longer generated.
- Deleting one mock document must not delete the file (shared); `delete_source/1` leaves files alone.

## Alternatives

- One copy per document (ADR-0014 naming `<id>.pdf`): thousands of 450 KB copies for 10000 boreholes.

## Consequences

- Supersedes the "mock documents point at no real file" part of ADR-0025.
- The asset ships in the release image under `priv/repo/assets/`; storage stays outside the image (`document_storage` volume).

## References

- ADR-0014, ADR-0025, ADR-0026
