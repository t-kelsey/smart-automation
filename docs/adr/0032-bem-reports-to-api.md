---
id: ADR-0032
date: 2026-10-17
author: jl
title: bem reports stage results and boreholes to the API (--to api)
---

# ADR-0032 – bem reports stage results and boreholes to the API (`--to api`)

## Context

The API has `POST /api/boreholes` (ADR-0031) and the stage write-back `PUT` endpoints (ADR-0030), but `bem --to api` still posted the flat `Borehole.to_api_dict()` to `/api/boreholes`, which the API does not accept (it expects `{borehole, layers, document_id}`). There is no upload endpoint, so documents only exist after `mix documents.backfill`.

## Decision

- New `bem/src/bem/api.py` (`ApiClient`): `PUT` for OCR, translation, triage sections, extraction result and sink result, `POST` for the borehole. `--api-url` is now the base URL (`http://localhost:4000/api`).
- The `document_id` is the input file's stem if it is a UUID (ADR-0014). Otherwise bem only creates the borehole (no link, no tracking) and logs a warning.
- Tracking `PUT`s are best effort (failures are logged). Only the `POST` decides success. A failed `POST` is reported as a failed `sink_result`; the other sections of that file are still processed, and the file is marked failed at the end.
- Extraction results are reported with status `ok`/`error` and the record as `extracted_fields`; `validation_issues` is empty for now because `extract()` only logs them.

## Pros

- No backend change; the contract in `bem/API_INTEGRATION.md` is used as written.
- `GET /api/documents/:id/pipeline_trace` shows what happened per document.

## Cons

- Without an upload endpoint, only backfilled documents get tracking.
- `POST` is not idempotent: re-running a document creates its boreholes again.

## Alternatives

- Add an upload endpoint so bem can create documents itself: not needed yet (ADR-0031).

## Consequences

- Passing `extract()` validation issues through to `validation_issues` is a possible follow-up.

## References

- ADR-0014, ADR-0030, ADR-0031, `bem/API_INTEGRATION.md`
