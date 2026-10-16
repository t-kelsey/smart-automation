"""Translate the OCR markdown to English, then extract borehole fields from it (ADR-0007).

Both steps are stubs for now. Translation and extraction still need a local backend
and a field mapping (ADR-0004). Until then the split step gets the markdown unchanged.
"""


def translate(markdown: str) -> str:
    # TODO: pick a local translation backend (target language: English).
    return markdown


def extract(markdown: str) -> str:
    # TODO: map the translated markdown onto Borehole/LogEntry fields; convert ft to m.
    return markdown
