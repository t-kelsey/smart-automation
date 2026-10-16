---
id: ADR-0007
date: 2026-10-16
author: Tyler Kelsey
title: OCR always runs first; translation, extraction and the per-borehole split work on its markdown output
---

# ADR-0007 – OCR always runs first; translation, extraction and the per-borehole split work on its markdown output

## Context

ADR-0001 put triage before OCR, and ADR-0003 used page selection to skip pages before OCR. Two things changed since then:

- Borehole data is mostly in tables. Table structure (depth columns, layer boundaries, sample rows) is what makes a log readable, so OCR has to be table-aware. This applies to digital PDFs too: their text layer loses table structure, so the text layer alone is not enough.
- Running OCR before triage means every later step works on text, including scanned files. The borehole ID split previously failed on scanned PDFs and images because there was no text to search.

## Decision

The pipeline runs in this order, for every input file:

1. **OCR (always).** A local, table-aware OCR engine (ADR-0008) converts the file to markdown. Digital PDFs are OCR'd too, not read from their text layer.
2. **Translation.** Translates the markdown to English. Works on the markdown file, not on raw input.
3. **Extraction.** Maps the translated markdown onto the borehole data format (ADR-0004).
4. **Split into API JSON.** Splits the markdown into one JSON object per borehole, shaped for the Elixir API. The split uses the borehole ID patterns from `bem/triage.py` (see below).

Consequences of the new order:

- **Triage before OCR is removed.** Format classification is no longer needed to choose a path, because every file goes through OCR.
- **Page selection (ADR-0003) is removed from the path.** It depended on text before OCR. Pages are no longer filtered out before OCR; dropping irrelevant pages can return later, on the markdown.
- **The borehole ID patterns move to the split step.** They run on the translated markdown, line by line, instead of on raw page text. The ID rules and depth filter are kept. The pypdf overprint fix is dropped, because OCR no longer reads a text layer.

This supersedes the stage order in ADR-0001 and the page-selection timing in ADR-0003. Their other decisions still hold, including the one-JSON-per-borehole shape and the Pydantic validation in ADR-0004.

## Pros

- Table structure is preserved for every input, including digital PDFs.
- Scanned files get a borehole split, which they didn't have before.
- The OCR markdown is a single, inspectable intermediate that can be cached (ADR-0006).

## Cons

- OCR runs on every page, including irrelevant report pages (for example the 100+ page full reports). This is the slowest part of the pipeline, so it costs the most time.
- The first step is the most expensive, so a failure there wastes the most work per file.

## Alternatives

- **Triage before OCR, as in ADR-0001.** Cheaper on long reports, but splits and skips text-less scanned files, and digital PDFs would skip table-aware OCR.
- **Two-pass OCR** (a low-resolution pass to find log pages, then full resolution on those). Keeps the cost down on long reports. Possible later; not part of this decision.

## Consequences

- `bem/ocr.py` is rewritten to produce markdown per file. It replaces the Tesseract baseline and the pypdf and pdf2image page handling.
- `bem/triage.py` no longer classifies or selects pages. It only splits the translated markdown into per-borehole sections.
- Translation and extraction stages take markdown as input and return structured records.
- The OCR markdown is the first stage output to cache (ADR-0006).

## References

- ADR-0001 (superseded in part: stage order)
- ADR-0003 (superseded in part: page selection before OCR)
- ADR-0004, ADR-0005, ADR-0006
- ADR-0008
