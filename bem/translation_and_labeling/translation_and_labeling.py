"""Translate the OCR markdown to DIN 4023 terms, then extract borehole fields from it (ADR-0007, ADR-0017, ADR-0018).

Translation is a glossary lookup with a local machine-translation fallback (din4023.py, mt.py).
Extraction is still a stub: it needs a field mapping (ADR-0004), so until then the split step
gets the markdown unchanged.
"""

import logging

from langdetect import DetectorFactory, LangDetectException, detect

from din4023 import translate_markdown
from mt import MarianTranslator, Translator

# langdetect is random unless seeded, and the same document must always give the same language.
DetectorFactory.seed = 0

log = logging.getLogger(__name__)


def detect_language(markdown: str) -> str:
    """Detect the language of a whole document. Cells are too short to detect reliably."""
    try:
        return detect(markdown)
    except LangDetectException:
        return "en"


def translate(markdown: str, translator: Translator | None = None) -> tuple[str, list[str]]:
    """Translate the markdown. Returns the translated markdown and every translate_error in it."""
    src = detect_language(markdown)
    log.info("source language: %s", src)
    return translate_markdown(markdown, src, translator or MarianTranslator())

