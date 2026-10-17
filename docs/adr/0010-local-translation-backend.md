---
id: ADR-0010
date: 2026-10-17
author: Tyler Kelsey
title: Open-source MarianMT models as the offline machine-translation fallback behind the DIN 4023 glossary
---

# ADR-0010 – Open-source MarianMT models as the offline machine-translation fallback behind the DIN 4023 glossary

## Context

ADR-0009 translates lithology cells with a glossary. Terms the glossary doesn't cover need a fallback that:

- is an open-source model that can be downloaded and then runs locally, with no paid service or API (ADR-0001: the data must not leave the machine),
- covers the source languages in our logs (Spanish, Danish, Norwegian, German, French, plus English),
- runs on CPU and works on the Python version the project requires (3.14).

The glossary stays the authority for the output. A machine translation is only used when it lands on a DIN 4023 term, so a bad translation can't produce a wrong designation silently.

## Decision

- **Backend:** MarianMT models from the Helsinki-NLP `opus-mt` family (MIT-licensed), loaded through `transformers`. One model per source language, translating to English (`opus-mt-es-en`, `opus-mt-da-en`, `opus-mt-de-en`, `opus-mt-fr-en`). The models are downloaded once from Hugging Face and then loaded from the local cache. Run with `HF_HUB_OFFLINE=1` after the download.
- **Norwegian:** no Norwegian model is assumed. Danish is used as the closest available model, to be checked on the first download.
- **Pipeline for each lithology cell** (in `bem/din4023.py`):
  1. expand source abbreviations (USCS group symbols such as `CH`, `SM`, and common log abbreviations such as `Sa`, `Cl`) to words, and expand DIN short forms (`U, t`) to their designations;
  2. exact glossary lookup;
  3. fuzzy correction of each word against glossary keys (difflib, cutoff 0.8), then lookup again;
  4. machine-translate the cell to English with the MarianMT model, then glossary lookup on the English result;
  5. if every stage fails, output `translate_error:<original text>`.
- **Acceptance rule:** a machine translation or fuzzy match is only used if it hits a glossary entry. Free machine output is never written into the record.
- **Source language** is detected once per document with `langdetect`, not per cell, since cells are too short to detect reliably.
- **Column gating:** only cells under a lithology-like table header are translated, so depths and numbers are never touched or reported as errors.
- **Output** is the full DIN designation. Short forms are not written into the cell text.

## Pros

- Open-source, downloadable, and offline after the one-time download; no paid service.
- Runs on CPU; each language model is a small download (about 300 MB).
- Works on the project's Python 3.14, unlike Argos Translate (argosopentech/argos-translate#517).
- The glossary still decides the output, so a poor machine translation can't introduce an unknown term.

## Cons

- The models must be downloaded once, with internet access, before the event.
- Machine translation of technical terms is unreliable. The glossary check catches most bad results, but not all.
- No Norwegian model is assumed, so Norwegian terms depend on the Danish model until checked.
- Pulls in `transformers`, `sentencepiece` and `langdetect`, on top of the PyTorch that Docling already installs.

## Alternatives

- **Argos Translate:** open source and offline, but `import argostranslate` fails on Python 3.14 (issue #517, caused by spaCy's pydantic v1 shim). Would need a separate Python 3.12 environment.
- **A local LLM via Ollama:** handles context better, but needs a larger model and more memory, and returns free text that still needs the same glossary check.
- **No fallback, errors only:** simplest, but leaves many terms as errors that a translation could have resolved.

## Consequences

- `bem/mt.py` wraps the MarianMT models behind a small `Translator` interface, so the backend can be swapped later. `NullTranslator` is used when no model is available.
- New dependencies in `bem/requirements.txt`: `transformers`, `sentencepiece`, `langdetect`.
- Models are downloaded once, for example by running a translation once with internet access. Cells that fail every stage are visible in the output as `translate_error:...`, so they can be added to the glossary.

## References

- ADR-0001, ADR-0007, ADR-0009
- Helsinki-NLP OPUS-MT models on Hugging Face: https://huggingface.co/Helsinki-NLP
- Argos Translate Python 3.14 issue: https://github.com/argosopentech/argos-translate/issues/517
