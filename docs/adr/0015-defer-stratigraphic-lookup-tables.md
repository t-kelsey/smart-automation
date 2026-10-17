---
id: ADR-0015
date: 2026-10-17
author: jl
title: Defer stratigraphic/lithology standardisation lookup tables
---

# ADR-0015 – Defer stratigraphic/lithology standardisation lookup tables

## Context

`stratigraphy` and `petrography` on `borehole_layers` are free-text strings. Adding lookup tables (`stratigraphic_units`, `lithologies`) was considered, to standardise and search across differently-named regional formations and material descriptions.

## Decision

Keep both as free text for now; do not implement lookup tables yet. `geologic_age` — an internationally standardised, chronostratigraphic value (ICS timescale) — is identified as the more realistic cross-region comparable axis than the formation name itself, but it is also not yet implemented; it's left as a documented future field.

## Pros

- Avoids building a cross-region formation-name-matching system that isn't reliably automatable: stratigraphic formation names are regionally defined (not a translation problem), so there's no 1:1 mapping between e.g. a German and an Australian formation name without a curated, human-maintained geological reference — out of scope for the hackathon.

## Cons

- Stratigraphy search/filtering across different countries' data won't be meaningfully comparable until this is addressed in some form.

## Alternatives

- A lookup table matching whole `petrography` phrases — rejected: petrography descriptions are compositional (base material + modifiers like roundness/grain size/secondary components), so whole-phrase matching doesn't generalise across combinations.
- A lookup table only for the base lithology category (e.g. Kies/Sand/Ton/Kalkstein), decoupled from modifiers — a reasonable middle ground, but deferred alongside stratigraphy for scope reasons.

## Consequences

- Task 3 (Standardisation) in the task doc keeps "consider a lookup/mapping table" as future-facing guidance rather than a concrete schema; revisit if there's time after core ingestion/map features work.

## References

- docs/elixir-backend-borehole-pipeline.md
