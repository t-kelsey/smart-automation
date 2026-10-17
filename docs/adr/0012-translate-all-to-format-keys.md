---
id: ADR-0012
date: 2026-10-17
author: Tyler Kelsey
title: Translate every label and value to a format key and its backend target, and propagate what cannot be translated
---

# ADR-0012 – Translate every label and value to a format key and its backend target, and propagate what cannot be translated

## Context

ADR-0009 to ADR-0011 translated lithology cells and kept everything else unchanged. The target is wider: every key in `BoreholeDataFormat.xlsx` is a translation target, and so are soil and rock types. Anything that can't be translated must be visible in the output instead of being silently left in the source language.

The backend (`docs/elixir-backend-borehole-pipeline.md`) stores values in two tables: `boreholes` (fixed columns plus a `metadata` map) and `borehole_layers` (depth range, stratigraphy, petrography, colour, plus `metadata`). Layer depth columns are not keys in the xlsx. The user decided they go to the layer table, marked so they can be routed there.

## Decision

- **Labels** (table headers, and the label part of `label: value` lines) resolve to a format key, through an exact match, a fuzzy match (labels of 5 or more characters), and machine translation to English. The key maps to its backend target path (`FORMAT_TARGETS` in `bem/format_keys.py`). A header that doesn't resolve becomes `translate_error:<header>`.
- **Layer depth columns** map to `borehole_layers.depth_from_m` and `borehole_layers.depth_to_m`. They are not xlsx keys, but the backend needs them.
- **Values** are translated by the kind of their target (`VALUE_KIND`):
  - `identifier`, `name`, `date`, `coordinate`, `crs`, `number`: kept unchanged. Extraction converts them later (ADR-0002, ADR-0004).
  - `soil`: DIN 4023 term (ADR-0009). Short values go through the glossary and machine translation (ADR-0010). Long values are machine-translated.
  - `colour`: colour words only (ADR-0011).
  - `text`: machine-translated to English. English text is kept as it is.
- **Table columns** take the value kind of their header's key. Columns whose header is an error keep their cells unchanged; the header error is already recorded.
- **Error propagation:** every `translate_error:<text>` is returned by `translate_markdown` and copied into `Borehole.translate_errors` (`bem/schema.py`) for the borehole whose section contains it (`bem/triage.py`). The API should keep such records unverified until someone resolves them.

## Pros

- Every label and value has a defined target, so the split step can route each value to its table.
- Errors are visible in the output and per borehole, so they can be reviewed and added to the glossary.
- Values that extraction converts later (IDs, coordinates, dates, numbers) are not damaged by translation.

## Cons

- Many headers and values will be `translate_error` until the label lists and glossary grow. The label lists in `FORMAT_LABELS` are hand-written.
- Long free text is machine-translated without a glossary check (chosen by the user). Errors in it are not caught the way glossary matches are.
- Records with errors are kept, not dropped, so the API must handle the `translate_errors` field.

## Alternatives

- **Refuse records with any error:** stricter, but would discard most of the data while the glossary is incomplete.
- **Map depth headers to `SampleDepth`:** wrong, since layer boundaries are not samples.

## Consequences

- Supersedes the column gating in ADR-0010 (only lithology columns were translated), and the header fallback in ADR-0011.
- `FORMAT_TARGETS` and `VALUE_KIND` must cover the same keys; the module checks this when imported.
- `translate()` returns `(markdown, errors)`. `Borehole` has a `translate_errors` field.
- The backend has no field for "location name", "project name" and similar values, so they go to `boreholes.metadata`.

## References

- ADR-0002, ADR-0004, ADR-0005
- ADR-0009, ADR-0010, ADR-0011 (partly superseded, see Consequences)
- `docs/elixir-backend-borehole-pipeline.md`, Data Model
- `data/HKBoreholeChallenge_Data_BFH2026/Standards_Formats/BoreholeDataFormat.xlsx`
