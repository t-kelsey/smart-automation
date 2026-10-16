---
id: ADR-0008
date: 2026-10-16
author: Tyler Kelsey
title: Docling as the local, table-aware OCR engine, with markdown as the interchange format
---

# ADR-0008 – Docling as the local, table-aware OCR engine, with markdown as the interchange format

## Context

ADR-0007 requires OCR to be table-aware and to run locally, because cloud vision models are too slow and too expensive for the hackathon budget (ADR-0001) and the data must stay on local machines. OCR is the slowest stage, so its output must also be easy to cache and inspect.

The Tesseract baseline in the code (ADR-0001 placeholder) reads text line by line and loses table structure. Our `pyproject.toml` already lists `docling`, and the team chose it when asked.

## Decision

- **Engine:** [Docling](https://github.com/docling-project/docling), run locally through `DocumentConverter`.
- **Always OCR:** the PDF pipeline is set to force full-page OCR (`force_full_page_ocr`), so the text layer is ignored and every page is read from its image. Table structure recognition stays on.
- **Output:** each input becomes one markdown file, exported with `export_to_markdown()`. Markdown is the interchange format between OCR, translation and extraction.
- **Scope:** docx files are not OCR'd. Docling reads them directly as structured text, and they contain no scanned pages. Images go through the same OCR path as PDFs.
- **Storage:** markdown files go to `bem/output/ocr/`, which is gitignored (it holds confidential text from `data/`).

## Pros

- Table structure survives as markdown tables, which the translation and extraction steps can read.
- Runs fully locally, so no data leaves the machine.
- Already a dependency of the project.

## Cons

- Docling is a large install and pulls in models on first run.
- Force full-page OCR is slower than using the text layer. This is an accepted cost for table quality (ADR-0007).
- The Docling API used here (`PdfPipelineOptions`, the OCR options class, `force_full_page_ocr`) was written from memory and has not been checked against the installed version yet. Check it on the first run.

## Alternatives

- **Tesseract** (current placeholder): fast and light, but loses table structure. Rejected for table-heavy data.
- **A local vision-language model** (for example Qwen2.5-VL via Ollama): better on handwriting, but much slower. Possible later for handwritten pages; the markdown interchange format does not change.
- **Docling's text layer only** (no forced OCR): skips OCR on digital PDFs, which ADR-0007 rules out.

## Consequences

- `bem/ocr.py` calls Docling and writes markdown; `pytesseract` and `pdf2image` are no longer needed.
- The OCR engine is local, so OCR results depend on the machine's hardware and the installed Docling version. Record the version with each run.

## References

- ADR-0001, ADR-0007
- Docling documentation (https://docling-project.github.io/docling/)
