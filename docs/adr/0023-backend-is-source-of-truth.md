---
id: ADR-0023
date: 2026-10-17
author: jl
title: Backend data model and API shape are the source of truth
---

# ADR-0023 – Backend data model and API shape are the source of truth

## Context

`web/` already had hand-written TypeScript types and mock data for a `Borehole` (`web/src/lib/components/borehole/types.ts`, `web/src/routes/borehole/[id]/mock-data.ts`) before `api/`'s data model and Map/Search API existed. The two now disagree in places: the frontend shape includes fields like `cause`, `client`, `location.place`, and structured `stratigraphy.code`/`name`, `petrography.lithology`/`description`, `color.hex`/`name` that don't exist (or exist differently) in the backend's `boreholes`/`borehole_layers` schema and `BoreholeJSON` response.

## Decision

`api/`'s data model and the JSON it actually returns (as documented in `docs/elixir-backend-borehole-pipeline.md` and the corresponding ADRs, in particular ADR-0012 and ADR-0013) is the single source of truth. Where the frontend's existing types/mock data disagree with it, the frontend updates its types and mock data to match the backend — not the other way around.

## Pros

- One authoritative schema instead of two independently evolving "ideal" shapes drifting apart.
- The backend schema is grounded in the real constraints of extracted borehole data (pervasive nullability, confidentiality rules excluding `documents.storage_path`/`raw_extraction` from any response, PostGIS geometry, many-to-many `documents`↔`boreholes`) that the frontend's hand-written mock data wasn't designed around.

## Cons

- Frontend work already done against the old mock shape needs to be adapted (types, mock data, any component logic assuming fields that don't exist on the backend).

## Alternatives

- Negotiate a shared schema upfront before either side implements anything — moot at this point, both sides already made independent progress under hackathon time pressure.
- Treat the frontend's shape as authoritative and retrofit the backend to match it — rejected: would mean adding fields/structure to the backend schema (e.g. `client`, `cause`, structured lithology) without first confirming they're actually extractable/needed data, purely to match a mock-up.

## Consequences

- Any field the frontend currently assumes that the backend doesn't have should be resolved by checking `docs/elixir-backend-borehole-pipeline.md` and `docs/adr/` first — if it's genuinely needed data, it gets added to the backend schema deliberately (with its own ADR if it's a non-trivial addition); otherwise the frontend drops or adapts its expectation.
- `CLAUDE.md` documents this rule under "Source of truth" so it's visible regardless of which app an agent is working in.

## References

- docs/elixir-backend-borehole-pipeline.md
- ADR-0012
- ADR-0013
- CLAUDE.md
