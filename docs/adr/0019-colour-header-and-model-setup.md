---
id: ADR-0019
date: 2026-10-17
author: Tyler Kelsey
title: Colour words, header fallback, Norwegian model order and a one-time model download
---

# ADR-0019 – Colour words, header fallback, Norwegian model order and a one-time model download

## Context

ADR-0017 and ADR-0018 left four open points:

- **Colour** was dropped from translated cells, though the brief says colour carries meaning. The colour field of the format is `Soil/Rockprofile` (color/pattern).
- **Norwegian** had no model: ADR-0018 used the Danish model as a stand-in.
- **Column detection** depended only on the table header text, which Docling sometimes garbles.
- **Setup** had no step for downloading the translation models before the event.

## Decision

- **Colour** (`bem/din4023.py`, `translate_colour`): colour words are mapped to German colour names, using the words of DIN 4023 Tables 1–3 and Annex A where they exist. Tints ("rojizo", "amarillento") are added in front of the base colour, and lightness ("claro", "oscuro") comes first. "castaño rojizo claro" → `hellrotbraun`. The colour is written after the soil name as `; Farbe: <colour>`. Colours without a DIN word (e.g. "weiß") use the nearest German name.
- **Norwegian** (`bem/mt.py`): the model list for `no` tries `Helsinki-NLP/opus-mt-no-en` first and falls back to the Danish model. This supersedes the Norwegian point in ADR-0018. The first download shows which one loaded.
- **Column detection** (`bem/din4023.py`, `_translate_table`): a column is lithology if its header matches a lithology keyword. If no header matches, the columns where at least one cell is a known glossary term are used instead. The `grund` keyword is removed, because "Grundvand" (groundwater) is not a lithology column.
- **Setup** (`bem/download_models.py`): one command downloads every candidate model while online. Runs then use `HF_HUB_OFFLINE=1`.

## Pros

- Colour is kept in the output, so the colour information in the logs is not lost.
- Norwegian gets its own model when it exists, and the Danish fallback is kept.
- Column detection still works when the header is garbled.
- The model download is a single documented step.

## Cons

- The colour mapping is a hand-written approximation. It needs review against real logs.
- The fallback column detection can pick up a column that is not lithology, when one of its cells happens to match a term.
- The Norwegian model name is unverified until the first download.

## Alternatives

- **Colour via machine translation:** colour words are short and well covered by the dictionary, so MT adds risk without benefit.
- **Headers only:** simpler, but fails silently when Docling garbles the header.

## Consequences

- Colour is written after the soil name in the cell, so the cell reads, for example, `Schluff, tonig; Farbe: hellrotbraun`.
- Unknown colour words are not reported as `translate_error`; they are left out of the output, since colours are only an extra field on top of the soil name.
- Run `python download_models.py` once, with internet access, before the event.

## References

- ADR-0017, ADR-0018
- DIN 4023:2023-02, Tables 1–3 and Annex A (colour words)
