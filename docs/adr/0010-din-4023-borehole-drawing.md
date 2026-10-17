---
id: ADR-0010
date: 2026-10-17
author: Kasimir Uihlein
title: DIN 4023 as the drawing standard for borehole cross sections
---

# ADR-0010 – DIN 4023 as the drawing standard for borehole cross sections

## Context

The borehole details view shows a cross section (column) of the layers. The first version used an ad-hoc lithology key with invented symbols. The challenge needs standardised, readable logs, and the project data folder contains DIN 4023:2023-02 (graphic representation of borehole results) and the hatch sheet "DIN 4023 Schraffuren" (identical to Table 1 of the standard).

The API currently stores `petrography` as free text. A layer can be a mix of components (for example "gravel, sandy, slightly silty"), which a single lithology key cannot express.

## Decision

- DIN 4023 is the drawing standard. The engine is pure TypeScript in `web/src/lib/din4023/` with no UI dependencies: materials (49 entries from Tables 1–3), Annex A colours, hatch pattern definitions, composition model, short-form and description formatting, and a free-text parser.
- A layer's petrography is a structured `Composition` (main component, secondary components with proportion weak/strong, optional breakdown for anthropogenic fill) instead of a single `LithologyKey`.
- The column is rendered only from layer data: a white background, an optional DIN colour tint, the main pattern at full width, the first secondary component's pattern on the right half, depth labels at boundaries and the short form (for example `G/S, u'`) next to each layer. Groundwater, samples and property symbols are not drawn for now.
- Hatch patterns are SVG `<pattern>` elements defined once (`PatternDefs`) and referenced by id.
- Until the API delivers structured compositions, `parseComposition` derives them from the free-text petrography. This is best effort and returns no composition when nothing is recognised.
- Where the 2023 tables differ from the older hatch sheet, the 2023 tables win.

## Pros

- Output follows a recognised standard, so geologists can read it without a custom legend.
- The engine is framework-free and reusable (for example for exports).
- The composition model expresses mixed soils exactly.
- Patterns are defined once, which keeps the DOM small.

## Cons

- The text parser is heuristic and can misread unusual wording; it covers English only.
- The standard's colour annex is inconsistent for "türkis"; we picked one value and documented it in `colors.ts`.
- Dropped features (water level, samples, property symbols) lose information the standard supports.
- No unit test runner exists in `web/`; the engine was checked with a Node smoke script and screenshots.

## Alternatives

- Keep the custom lithology key: simple, but not standard-conformant and cannot express mixtures.
- Use pre-rendered image hatches: easier to match the sheet exactly, but not scalable or recolourable.
- Render the full standard including property symbols: more complete, but judged overly complex for the current need.

## Consequences

- `BoreholeLayer.petrography` changes to `{ composition?, description }`; mappers and mock data were updated.
- The API should eventually store the composition in structured form; the parser can then be removed.
- Further symbols from the standard can be added later as separate, optional layers of the column.

## References

- DIN 4023:2023-02, Table 1–3, Annex A (`data/Standards_Formats/`, confidential, not committed)
- ADR-0009 – Frontend layered data architecture
