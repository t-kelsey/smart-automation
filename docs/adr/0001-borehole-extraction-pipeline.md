---
id: ADR-0001
date: 2026-10-17
author: Tyler Kelsey
title: Staged borehole extraction pipeline in Python (bem/)
---

# ADR-0001 – Staged borehole extraction pipeline in Python (bem/)

## Context

Raw borehole data comes as digital PDFs, scanned PDFs, images (often handwritten) and docx files, in several languages. A single input file can contain one or more boreholes, and a batch can contain one or more files. The data has to end up in a PostGIS database in the format defined in `data/.../Standards_Formats/BoreholeDataFormat.xlsx` (borehole metadata, per-depth log data, optional sample test results). The database sits behind the Elixir API in `api/`.

## Decision

A Python pipeline in `bem/` with four processing stages, run by `bem/main.py`, followed by an output step:

1. **OCR** (`ocr.py`): convert every input format (digital PDF, scanned PDF, image, docx) into one unified text base format (`TextDocument`). Digital PDFs use their text layer; scans and images are OCR'd.
2. **Translation** (`translation.py`): translate all terms in the text to English.
3. **Triage** (`triage.py`): split the text into individual boreholes (`BoreholeText`) and drop irrelevant parts.
4. **Extraction** (`extraction.py`): for each borehole, extract the fields defined in the borehole data format into a `Borehole` record. The result is JSON.
5. **Output** (`output.py`): send the JSON to the Elixir API, save it as JSON files, or print it to the terminal (`--to api|json|print`). The API writes the records to PostGIS.

Triage runs on the unified text, not on the raw files, so it has one code path for every input format. Translation runs before triage, so every later stage works on English text.

Stage outputs (`TextDocument`, `BoreholeText`, `Borehole`) are plain data types defined in `models.py`.

OCR stays a separate stage from translation and extraction. We considered a single cloud vision-language model call that does OCR, translation and extraction together. We rejected it for now because it is too expensive and too slow for the hackathon budget.

**OCR is an open problem that we will solve later.** For now `ocr.py` is a placeholder/basic implementation, so the pipeline works end-to-end on digital documents first.

## Pros

- Each stage can be built, tested and swapped on its own (for example a better OCR engine later).
- Digital PDFs skip OCR completely: their text layer is cheap and exact.
- Triage and extraction have one input type, so they do not need per-format logic.
- No per-page cloud vision cost or latency.

## Cons

- Classic OCR loses table layout (depth columns, layer boundaries) and does badly on handwriting, so accuracy on scanned and handwritten logs will be low until OCR is solved.
- Text passes between stages, so errors from one stage carry into the next.
- Translating before triage also translates text that triage later drops. This costs extra time, but it keeps triage and extraction on a single language.
- Triage depends on the text keeping the borehole boundaries and headers that OCR and translation produce. If those are lost, splitting fails.

## Alternatives

- **A single cloud vision LLM call** (OCR + translation + extraction in one): most accurate on handwriting and layout, but rejected for cost and speed.
- **A local vision model** (for example Qwen2.5-VL): no API cost, but slow and needs strong hardware. We may revisit it when we solve OCR.
- **Triage on the raw files, before OCR** (the earlier design): sorts files by type and decides which need OCR. Rejected because it needs a separate split path for each input format. It also makes triage and translation depend on the format of each file.

## Consequences

- This ADR replaces the earlier stage order (triage before OCR, and a combined translation-and-extraction module). The change was made by editing this ADR in place, so the history of the decision is kept in git.
- Scanned and handwritten inputs are a known weak spot. A follow-up ADR should record the OCR choice.
- Stage outputs are plain data passed between modules, so a later merge of the stages is still possible. Caching of stage outputs is covered by [ADR-0006](0006-cache-stage-outputs.md).

## References

- `data/HKBoreholeChallenge_Data_BFH2026/Standards_Formats/BoreholeDataFormat.xlsx`
- DIN 4023
