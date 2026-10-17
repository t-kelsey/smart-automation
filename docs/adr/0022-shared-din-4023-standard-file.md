---
id: ADR-0022
date: 2026-10-17
author: Kasimir Uihlein
title: Shared DIN 4023 standard file for bem, api and web
---

# ADR-0022 – Shared DIN 4023 standard file for bem, api and web

## Context

All three components need the same vocabulary for soils and rocks: `bem` normalises extracted lithology, `api` stores and validates it, and `web` draws it (ADR-0021). Today the only encoding of DIN 4023 is TypeScript in `web/src/lib/din4023/` (materials, colours, patterns), so `bem` (Python) and `api` (Elixir) cannot use it and would have to copy it by hand. Copies drift, and the sources already disagree in places:

- `data/Standards_Formats/DIN 4023.pdf` is the 2023-02 edition (replaces 2006-02), while the hatch sheet `DIN 4023 Schraffuren.pdf` is 2006-02.
- The 2023 Table 1 adds "Grobschluff" and "Großer Block", which have no hatch on the 2006 sheet.
- Annex A lists "türkis" as RGB 98, 213, 196 but hex #28A9B2.

## Decision

- The standard is kept as one language-neutral data file, `standards/din-4023/din-4023.json`, at the repository root. It is the single source of truth for `bem`, `api` and `web`.
- The content is German, as in the standard. Contents:
  - `schraffuren`: the 47 hatches of the 2006-02 sheet, each with a stable ASCII `id`, the sheet label, category (`boden`, `fels`, `geologisch`), short form and source table.
  - `tabelle_1`: the 17 pure soil types of Table 1 (names, main/secondary short forms, `schraffur` id, colour).
  - `farben`: the Annex A colours (RGB, hex, RAL), referenced by name from Table 1.
  - `norm`: edition and source metadata.
- Table 1 follows the 2023-02 edition, since that is the document we have. Rows added in 2023 carry a `hinweis`; "Großer Block" has `schraffur: null` and "Grobschluff" reuses the `schluff` hatch.
- Source inconsistencies (türkis) are kept as printed and annotated; the hex value is used for rendering, matching `web/src/lib/din4023/colors.ts`.
- Components read this file, or generate code from it, instead of maintaining their own tables. Moving `web` over is a separate step.
- The file contains only names, short forms and colour values, no hatch artwork. Pattern drawing stays in `web`.

## Pros

- One definition for three languages; no hand-copied tables.
- Hatch ids and colour names give a stable key for the API and database.
- Provenance is explicit: edition per table, and known deviations are annotated.
- Plain JSON is trivial to load in Python, Elixir and TypeScript and easy to diff in review.

## Cons

- Tables 2 to 6 of the standard are not covered. Rock and geological names appear only as hatch entries (id, label, short form).
- Mixing editions (2006-02 hatches, 2023-02 Table 1) can confuse; it is documented in the file but must be kept in mind.
- English names and the existing TypeScript keys (`gravel`, `coarseGravel`, …) are not in the file, so `web` needs a mapping from hatch id until it migrates.
- The content is derived from a confidential, licensed standard in `data/`. Names, short forms and colour values are standard facts, but the repository owner should confirm that publishing them is acceptable before the repo leaves the hackathon.
- The file was transcribed by hand from PDFs and has no automated check against them.

## Alternatives

- Keep the TypeScript module as the only source: no new file, but `bem` and `api` cannot consume it.
- Per-component copies (Python dict, Elixir module): fast to start, but drift is likely.
- Store the standard in the database via API seeds: usable for `api` and `web`, but `bem` runs before and independently of the API.
- Include English translations in the JSON: convenient for `web`, but the request was for a German standard file; translations can be added as extra fields later.

## Consequences

- `bem`, `api` and `web` should reference ids from this file for hatches and Table 1 soil types.
- ADR-0021 states 49 materials and that the sheet equals Table 1. The sheet actually holds 47 hatches and covers more than Table 1. This ADR does not change ADR-0021; the file is a reference, not a replacement.
- Extending coverage (Tables 2 to 6) or adding English labels means editing this file and noting it in a new ADR.
- If the licence question above is answered "no", the file moves out of version control and is loaded from `data/`.

## References

- `standards/din-4023/din-4023.json`
- DIN 4023:2023-02, Table 1 (p. 10) and Annex A, Table A.1 (p. 17); DIN 4023 Schraffuren, 2006-02 (`data/Standards_Formats/`, confidential, not committed)
- ADR-0021 – DIN 4023 as the drawing standard for borehole cross sections
- ADR-0009 – Frontend layered data architecture
