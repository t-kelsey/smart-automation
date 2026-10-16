---
id: ADR-0003
date: 2026-10-16
author: Tyler Kelsey
title: Triage normalises inputs, selects relevant pages and splits per borehole
---

# ADR-0003 – Triage normalises inputs, selects relevant pages and splits per borehole

## Context

The inputs come in mixed forms. Some are digital PDFs, some are scanned PDFs, some are images and some are docx files. Some sources are folders of images that together make one document (for example `MEA03-jpg/`). Others are long full reports where only a few pages are borehole logs (`FullReport*.pdf`). And some documents hold several boreholes (BH-1 … BH-7). If each file goes downstream as a single unit, we waste OCR time and the extraction step sees a lot of noise.

## Decision

Triage (`bem/triage.py`) does more than classify the file type:

- **Normalise the format.** For a digital PDF, take the text layer. For a scanned PDF or an image, produce page images for OCR. For a docx, take the text. A folder of images is treated as one document.
- **Select pages.** Keep only the pages that look like borehole logs, using a simple keyword or heuristic check (terms such as depth, borehole, Bohrung or sondaje). The other pages are dropped before OCR and extraction.
- **Split per borehole.** When a document holds several boreholes, split it so that later stages produce one record per borehole.

## Pros

- Less OCR work, and less irrelevant text reaches extraction.
- Every later stage receives one standard document shape.

## Cons

- A keyword heuristic will sometimes drop a relevant page or keep an irrelevant one.
- Splitting per borehole is heuristic, and on unusual layouts it can merge or split boreholes wrongly.

## Alternatives

- Send every page downstream: simpler, but slower and noisier.
- A model-based page classifier: more accurate, but costly (see ADR-0001).

## Consequences

- Triage outputs a list of documents, where each one is a single borehole with its relevant pages.
- On scanned pages, page selection can only run after OCR, or with a cheap low-resolution OCR pass.

## References

- ADR-0001
