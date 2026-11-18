"""Word boxes of a PDF's text layer (`pdftotext -bbox`, poppler) to tighten the validator's boxes.

All boxes are `[x0, y0, x1, y1]` in 0-1 of the page, origin top left (ADR-0006).
"""

import pathlib
import re
import subprocess

from .ai import log

Box = list[float]
MARGIN = 0.01  # a word counts as inside a model box if its centre lies within the box grown by this

_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">')


def words(pdf: pathlib.Path) -> dict[int, list[Box]]:
    """1-based page -> normalised word boxes; pages without text (scans) are left out.
    Returns {} if pdftotext is missing or fails."""
    try:
        html = subprocess.run(
            ["pdftotext", "-bbox", str(pdf), "-"], check=True, capture_output=True, timeout=120
        ).stdout.decode(errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log(f"pdftotext failed on {pdf.name}, keeping the model's boxes: {e}")
        return {}
    pages: dict[int, list[Box]] = {}
    for i, (w, h, body) in enumerate(_PAGE.findall(html), 1):
        w, h = float(w), float(h)
        boxes = [[float(a) / w, float(b) / h, float(c) / w, float(d) / h] for a, b, c, d in _WORD.findall(body)]
        if boxes and w > 0 and h > 0:
            pages[i] = boxes
    return pages


def tighten(box: Box, page_words: list[Box] | None, margin: float = MARGIN) -> Box:
    """The union of the words whose centre lies inside `box` (grown by `margin`), else `box`."""
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    inside = [w for w in page_words or [] if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
    if not inside:
        return box
    return [min(w[0] for w in inside), min(w[1] for w in inside), max(w[2] for w in inside), max(w[3] for w in inside)]
