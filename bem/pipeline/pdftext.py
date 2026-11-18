"""Word boxes of a PDF's text layer (`pdftotext -bbox`, poppler) to tighten the validator's boxes.

All boxes are `[x0, y0, x1, y1]` in 0-1 of the page, origin top left (ADR-0006).
"""

import pathlib
import re
from html import unescape as html_unescape
import subprocess

from .ai import log

Box = list[float]
Word = tuple[Box, str]  # normalised box and the word's text
MARGIN = 0.01  # a word counts as inside a model box if its centre lies within the box grown by this
NEAR = 0.15  # a word matching the value counts if its centre is this close to the model box (page share)

_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def words(pdf: pathlib.Path) -> dict[int, list[Word]]:
    """1-based page -> normalised word boxes with their text; pages without text (scans) are left out.
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
        boxes = [
            ([float(a) / w, float(b) / h, float(c) / w, float(d) / h], html_unescape(text))
            for a, b, c, d, text in _WORD.findall(body)
        ]
        if boxes and w > 0 and h > 0:
            pages[i] = boxes
    return pages


def _union(boxes: list[Box]) -> Box:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _centre(b: Box) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def tighten(box: Box, page_words: list[Word] | None, margin: float = MARGIN) -> Box:
    """The union of the words whose centre lies inside `box` (grown by `margin`), else `box`."""
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    inside = [w for w, _ in page_words or [] if x0 <= _centre(w)[0] <= x1 and y0 <= _centre(w)[1] <= y1]
    return _union(inside) if inside else box


def _number(text: str) -> float | None:
    m = re.fullmatch(r"[^\d-]*(-?\d+(?:[.,]\d+)?)[^\d]*", text)
    return float(m.group(1).replace(",", ".")) if m else None


def _matches(text: str, values: list) -> bool:
    for v in values:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            n = _number(text)
            if n is not None and abs(n - v) < 1e-6:
                return True
        elif isinstance(v, str):
            word = re.sub(r"\W", "", text).lower()
            if len(word) >= 2 and word in {re.sub(r"\W", "", t).lower() for t in v.split()}:
                return True
    return False


def snap(box: Box, page_words: list[Word] | None, values: list) -> Box:
    """The box of the written value: words matching one of `values` (numbers compared as numbers,
    so 9,40 matches 9.4; strings word by word) near the model's `box`, the closest one plus the
    matching words on its line. Falls back to `tighten` if the value is not found there."""
    cx, cy = _centre(box)
    hits = [w for w, text in page_words or [] if _matches(text, values)]
    near = [w for w in hits if abs(_centre(w)[0] - cx) <= NEAR + (box[2] - box[0]) / 2 and abs(_centre(w)[1] - cy) <= NEAR / 2 + (box[3] - box[1]) / 2]
    if not near:
        return tighten(box, page_words)
    best = min(near, key=lambda w: (_centre(w)[0] - cx) ** 2 + (_centre(w)[1] - cy) ** 2)
    height = best[3] - best[1]
    line = [w for w in near if abs(_centre(w)[1] - _centre(best)[1]) <= height * 1.5 and abs(_centre(w)[0] - _centre(best)[0]) <= 0.3]
    return _union(line)
