---
id: ADR-0001
date: 2026-10-16
author: Tyler Kelsey
title: Staged borehole extraction pipeline in Python (bem/)
---

# ADR-0001 – Staged borehole extraction pipeline in Python (bem/)

## Context

Raw borehole data comes as digital PDFs, scanned PDFs, images (often handwritten) and docx files, in several languages. It has to end up in a PostGIS database in the format defined in `data/.../Standards_Formats/BoreholeDataFormat.xlsx` (borehole metadata, per-depth log data, optional sample test results). The database sits behind the Elixir API in `api/`.

## Decision

A Python pipeline in `bem/` with four separate stages, run by `bem/main.py`:

1. **Triage** (`triage.py`): sort each input file by type (digital PDF, scanned PDF/image, docx) and decide whether it needs OCR.
2. **OCR** (`ocr.py`): turn scanned or handwritten pages into text.
3. **Translation and extraction** (`translation_and_extraction.py`): translate the text and pull out the fields defined in the borehole data format.
4. **Load**: POST the extracted records as JSON to the Elixir API, which writes them to PostGIS.

OCR stays a separate stage from translation and extraction. We considered a single cloud vision-language model call that does OCR, translation and extraction together. We rejected it for now because it is too expensive and too slow for the hackathon budget.

**OCR is an open problem that we will solve later.** For now `ocr.py` is a placeholder/basic implementation, so the pipeline works end-to-end on digital documents first.

## Pros

- Each stage can be built, tested and swapped on its own (for example a better OCR engine later).
- Digital PDFs skip OCR completely: their text layer is cheap and exact.
- No per-page cloud vision cost or latency.

## Cons

- Classic OCR loses table layout (depth columns, layer boundaries) and does badly on handwriting, so accuracy on scanned and handwritten logs will be low until OCR is solved.
- Text passes between stages, so errors from one stage carry into the next.

## Alternatives

- **A single cloud vision LLM call** (OCR + translation + extraction in one): most accurate on handwriting and layout, but rejected for cost and speed.
- **A local vision model** (for example Qwen2.5-VL): no API cost, but slow and needs strong hardware. We may revisit it when we solve OCR.

## Consequences

- Scanned and handwritten inputs are a known weak spot. A follow-up ADR should record the OCR choice.
- Stage outputs are plain data passed between modules, so a later merge of the stages is still possible.

## References

- `data/HKBoreholeChallenge_Data_BFH2026/Standards_Formats/BoreholeDataFormat.xlsx`
- DIN 4023
