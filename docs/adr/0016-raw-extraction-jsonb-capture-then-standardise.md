---
id: ADR-0016
date: 2026-10-17
author: jl
title: raw_extraction is a tracking side-artifact, not a separate pipeline phase
---

# ADR-0016 – raw_extraction is a tracking side-artifact, not a separate pipeline phase

## Context

Borehole profiles reach `api/` via an external OCR/extraction service (a classic OCR engine, or more likely an LLM-vision service given the handwritten sources — not yet chosen, see the Elixir backend task doc's "Open Questions"). Its response format is unknown and will vary by provider.

An earlier version of this ADR described `raw_extraction` capture and standardisation as two deliberately decoupled phases (store the raw response first, map it to `boreholes`/`borehole_layers` in a separate later step). That is **not** the intended design — this revision corrects it.

## Decision

Ingestion is a **single pass**, done in one job/step:

1. Call the extraction service, get its response back.
2. Immediately figure out which fields are relevant and map them directly into `boreholes`/`borehole_layers` structs (unit conversion, coordinate reprojection, vocabulary normalisation happen right here), then insert them.
3. Along the way, also store the raw, unmodified response in `documents.raw_extraction` (Ecto `:map`, Postgres `jsonb`) — not as a required input to some later processing step, just as a side artifact for tracking/debugging.

`raw_extraction` exists purely so that if the mapping in step 2 produced something wrong or incomplete, a human can look at what the extraction service actually returned. It is not read by any other part of the pipeline.

## Pros

- One pass, one mental model: a document's extraction either fully succeeds (borehole + layers exist, `raw_extraction` stored alongside) or fails (`status: "failed"`, nothing half-done in `boreholes`).
- Fields the service returns but that aren't mapped to a column aren't silently lost — they're still visible in `raw_extraction` for debugging, even though nothing automatically re-reads them later.
- A reviewer can compare `raw_extraction` against the standardised fields to spot-check the mapping was done correctly.

## Cons

- `raw_extraction` has no schema of its own, so if someone *does* want to reprocess it later, that code must handle missing/differently-shaped keys defensively.
- If the mapping logic improves later, there's no built-in "replay" mechanism — reprocessing historical documents would mean writing one-off code to read `raw_extraction` back out, not a standing pipeline stage.

## Alternatives

- Treat capture and standardisation as two separate, independently-schedulable phases (the previous version of this ADR) — rejected: this is not simpler for the hackathon scope, and `raw_extraction` is only meant as a debugging aid, not a durable intermediate representation to be replayed against.

## Consequences

- The ingestion job (Task 2) is responsible for calling the extraction service, mapping its response into `boreholes`/`borehole_layers`, and storing the raw response in `documents.raw_extraction` — all in the same job, ideally the same DB transaction.
- Nothing should depend on `raw_extraction`'s shape for anything other than manual inspection/debugging.

## References

- docs/elixir-backend-borehole-pipeline.md
- ADR-0011
- ADR-0012

