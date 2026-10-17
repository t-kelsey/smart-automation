---
id: ADR-0017
date: 2026-10-17
author: Tyler Kelsey
title: Translate soil and rock terms with a DIN 4023 glossary instead of an LLM
---

# ADR-0017 – Translate soil and rock terms with a DIN 4023 glossary instead of an LLM

## Context

ADR-0007 puts translation after OCR. The target is the vocabulary of DIN 4023 (Tables 1–3, the soil, rock and geological-name tables) and the `Lithology/SoilName` and `StratigraphicName` fields in `BoreholeDataFormat.xlsx`. The lithology terms in our sample logs are mostly English, with Spanish (SAM01), Danish (EUR01) and some Norwegian (ToughOne). Many lithology cells are short phrases such as "Limo arcilloso, castaño rojizo claro".

ADR-0001 rules out cloud models for cost and speed, and a local LLM would need a model download and a GPU we haven't set up. The vocabulary is also small and closed: DIN 4023 defines a fixed set of designations and short forms.

## Decision

Translation is a dictionary lookup, implemented in `bem/din4023.py`:

- **Main terms** (Tables 1–3) map a source word to its DIN designation and short form, for example `sand`/`arena` → Sand (S), `silt`/`limo` → Schluff (U), `clay`/`arcilla`/`ler` → Ton (T).
- **Qualifiers** map adjectives to their Nebenanteil (secondary-component) form, for example `sandy`/`arenoso` → sandig (s), `clayey`/`arcilloso`/`leret` → tonig (t).
- **Compound phrases** combine them as DIN does: the main term gives the name and short form, with secondary terms after it. "Limo arcilloso arenoso" → `Schluff, tonig, sandig (U, t, s)`.
- **Scope of replacement:** `translate()` only rewrites markdown table cells that are short (six words or fewer) and contain a recognised main term. Long descriptions are left alone. Original text stays in the OCR markdown (`bem/output/ocr/`).
- **Unknown terms** are left unchanged, so nothing is lost.

## Pros

- Deterministic and offline, so no data leaves the machine (ADR-0001).
- Output uses the DIN designations and short forms the format expects.
- Easy to extend: each new term is one line in the glossary, and the review is quick.

## Cons

- It only covers words in the glossary. Ambiguous terms (such as Danish "kalk", which can mean chalk or limestone) need a human decision.
- Colours, grain-size qualifiers in Spanish ("arena fina") and multi-sentence descriptions are not handled.
- Coverage of other languages will be incomplete until we test against more logs.

## Alternatives

- **Local LLM translation** (for example a small instruction model via Ollama): handles free text and ambiguity, but adds a model dependency and is slower. Possible later for long descriptions; the glossary stays as the fixed vocabulary for the output.
- **Using an online translation API**: rejected, because the data must not leave the machine.

## Consequences

- `bem/din4023.py` is the source of truth for the vocabulary; extend it when logs show unknown terms.
- `translate()` in `bem/translation_and_extraction.py` calls it on the OCR markdown before extraction.
- Ambiguous mappings are marked in the glossary, so they can be reviewed before the event.

## References

- ADR-0001, ADR-0007
- DIN 4023:2023-02, Tables 1–3 (`data/HKBoreholeChallenge_Data_BFH2026/Standards_Formats/DIN 4023.pdf`)
- `BoreholeDataFormat.xlsx`, fields `Lithology/SoilName`, `StratigraphicName`, `EngineeringSoilUnit`
