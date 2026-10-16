---
id: ADR-0004
date: 2026-10-16
author: Tyler Kelsey
title: Validate and normalise extracted records with Pydantic inside the extraction stage
---

# ADR-0004 – Validate and normalise extracted records with Pydantic inside the extraction stage

## Context

Extracted values arrive in mixed units (the format standard says "if ft, transfer to m"), mixed number formats and mixed date formats, and with fields missing. The API needs records that are consistent and match the format defined in `BoreholeDataFormat.xlsx`.

## Decision

Validation and normalisation are part of `bem/translation_and_extraction.py`, not a separate stage. The output records are defined as **Pydantic models** that mirror the borehole data format (metadata, log entries, sample tests). Validation does the following:

- converts ft to m, and decimal commas to points
- parses dates to ISO 8601
- checks that each depth interval has from ≤ to
- flags missing required fields and records them on the record instead of failing

## Pros

- The format is defined in one place and checked before anything reaches the API.
- Keeping it inside extraction means the pipeline has no extra stage, as requested.
- Pydantic models give us JSON serialisation for the API call for free.

## Cons

- The extraction module carries more responsibility.
- New dependency: pydantic.

## Alternatives

- A separate validate/normalise stage: cleaner separation, but more plumbing than a hackathon needs.
- Validation only in Elixir (Ecto changesets): bad values are only caught after a network round trip, and unit conversion still has to happen somewhere.

## Consequences

- The current dataclasses in `translation_and_extraction.py` have to be replaced by Pydantic models.
- The Ecto changesets on the API side can stay thin, because the input already matches the format.

## References

- ADR-0001
- `data/HKBoreholeChallenge_Data_BFH2026/Standards_Formats/BoreholeDataFormat.xlsx`
