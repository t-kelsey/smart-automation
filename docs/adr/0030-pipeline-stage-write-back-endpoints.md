---
id: ADR-0030
date: 2026-10-17
author: jl
title: Pipeline stage write-back endpoints (OCR/translation/triage/extraction/sink tracking)
---

# ADR-0030 – Pipeline stage write-back endpoints (OCR/translation/triage/extraction/sink tracking)

## Context

`docs/elixir-backend-borehole-pipeline.md`'s "Proposed Extension: Pipeline Stage Tracking" section designed a write path for `bem/` to report what each of its five stages (OCR, translation, triage, extraction, output; ADR-0001) produced for a document — today the only visibility is a local, gitignored, per-developer file cache (ADR-0006) and `documents.raw_extraction`, a single JSONB blob written at the very end of ingestion (ADR-0016). Neither lets the team inspect what happened with one specific document while debugging, nor where triage split a document into several borehole candidates.

## Decision

Implemented exactly as designed in that section:

- Four tables: `pipeline_stage_runs` (one row per `(document, stage)`, `stage` is `"ocr"` or `"translation"`), `triage_sections` (one row per borehole candidate within a document — the fan-out point), `extraction_results` and `sink_results` (1:1 children of `triage_sections` and `extraction_results` respectively, `on_delete: :delete_all`).
- Four endpoints, all `PUT` (upserts, safe to call again for the same document/stage/section):
  - `PUT /api/documents/:document_id/pipeline_stages/:stage`
  - `PUT /api/documents/:document_id/triage_sections` (replaces all sections for the document; deleting them cascades to `extraction_results`/`sink_results`)
  - `PUT /api/documents/:document_id/triage_sections/:section_index/extraction_result`
  - `PUT /api/documents/:document_id/triage_sections/:section_index/sink_result`
- Latest run only — no append-only history, consistent with the original design decision.
- Debug/internal only: nothing here is ever serialised in a public API response, same rule as `storage_path`/`raw_extraction` (ADR-0014).

`bem/API_INTEGRATION.md` documents the contract for whoever wires up `bem/`'s output.

## Pros

- A reviewer can inspect exactly what OCR/translation produced and where triage/extraction failed, per document, without reading log files on a developer's machine.
- `PUT`-based upserts mean `bem/` can re-run and re-report without creating duplicate rows or needing to track what it already reported.

## Cons

- No history across reruns — can't compare "did this BEM code change actually help" without re-adding an append-only variant later.
- `output`/`extracted_fields`/`validation_issues` are free-form `jsonb`, so nothing stops them becoming a dumping ground (same trade-off as `raw_extraction`, ADR-0016).

## Alternatives

- Two separate tables for OCR and translation instead of one `pipeline_stage_runs` table with a `stage` discriminator — rejected (see chat discussion during implementation): both stages are structurally identical (document-level, latest-run-only, same lifecycle columns), so a discriminator column is more idiomatic here and matches the single parameterised endpoint design.
- A materialised view or stored join across all four tables — rejected: low-volume point lookups by `document_id` don't need precomputed joins; a plain context function/query is simpler and sufficient.

## Consequences

- `docs/elixir-backend-borehole-pipeline.md`'s "Proposed Extension" section is now a record of the design, not a proposal — implemented as described.
- `docs/data-model.md`'s ER diagram reflects these tables under "Implemented", not "Proposed".

## References

- ADR-0001, ADR-0006, ADR-0014, ADR-0016, ADR-0017, ADR-0023
- docs/elixir-backend-borehole-pipeline.md
- bem/API_INTEGRATION.md
