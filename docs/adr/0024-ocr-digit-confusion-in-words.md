---
id: ADR-0024
date: 2026-10-17
author: Tyler Kelsey
title: Correct single OCR digits inside words before translation, and pass through values with several digits
---

# ADR-0024 – Correct single OCR digits inside words before translation, and pass through values with several digits

## Context

OCR often reads a letter as a look-alike digit inside a word: "Ki3s" for "Kies", "Ton1g" for "Tonig". Such a word misses the DIN 4023 glossary and machine translation, so the whole cell becomes a `translate_error:` (ADR-0020). The reverse also happens with codes: tokens such as "BK2O25" or "202a" contain several digits and are identifiers, not words. Sending them to translation only produces noise errors.

## Decision

Every whitespace-separated token in a header or value is checked before translation (`_fix_ocr_digits` in `bem/translation_and_extraction/din4023.py`):

1. **One digit and at least three letters:** the digit is replaced by the letter OCR most likely misread it as (`DIGIT_TO_LETTER`: 0→o, 1→l, 2→z, 3→e, 4→a, 5→s, 6→g, 8→b). The corrected text is then translated as normal.
2. **Two or more digits in one token:** that token is kept unchanged. In a comma-separated value, the segment containing it is kept as written and the other segments are translated, so "Sand, 10-12 m" becomes "Sand, 10-12 m" with "Sand" translated. A header containing such a token passes through unchanged. No `translate_error` is recorded for these tokens.
3. **Tokens with one digit and fewer than three letters** (units and short IDs such as "P1", "m3") are left unchanged.
4. If the corrected text still cannot be translated, the `translate_error:` carries the original text, not the corrected one.

Values that are already numbers, dates or dashes are kept before this check runs, as before (ADR-0020).

## Pros

- Single-digit OCR confusions in common soil words can now reach the glossary.
- Codes and IDs with several digits are no longer reported as untranslatable.
- Errors still point at the text as it appeared in the source, so they can be checked against the scan.

## Cons

- The digit-to-letter map is a guess. "1" can stand for "i" or "l", and "0" for "o" or "O". Only one candidate is tried per digit.
- A real word with a digit and three or more letters is altered (for example "A4Pap" becomes "AaPap"), and a corrected word can match a glossary entry by accident.
- Segments are split on commas only. A code without a comma, such as "Sand 10-12 m", keeps the whole value unchanged, so "Sand" is not translated there.
- Translating comma segments one at a time can lose qualifiers that span segments (for example "sandig, kiesig" in one cell with a code).
- Labels in `"label: value"` lines are not corrected. Only headers and values are.

## Alternatives

- **Try every candidate letter for each digit and keep the first that hits the glossary:** more accurate, but it multiplies lookups and can match the wrong word.
- **Report multi-digit tokens as `translate_error:`:** keeps them visible for review, but fills the error list with identifiers that are not translation problems.

## Consequences

- Refines the error handling in ADR-0020: the `translate_error:` rule now applies only after the digit check.
- Values with a multi-digit token are split on commas, and only the segments without such tokens are translated.

## References

- ADR-0017 (DIN 4023 glossary)
- ADR-0020 (translate every label and value to a format key)
