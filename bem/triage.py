"""Triage: turn raw input files into per-borehole documents (ADR-0001, ADR-0003).

For every input this module
1. classifies it (digital/scanned PDF, image, image folder, docx),
2. normalises it into a list of pages, with text where we already have it,
3. drops pages that clearly aren't borehole logs, and
4. splits what remains into one Document per borehole.

Pages without a text layer are kept as-is (text=None) for the OCR stage; we can't
judge their relevance or borehole ID until we can read them.
"""

import logging
import re
from collections.abc import Iterable, Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, computed_field

log = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# A PDF page with fewer extractable characters than this is treated as scanned.
# Scanned PDFs in our sample still yield a stray character or two per page
# (form feeds, watermarks), so "no text" is not a usable test.
MIN_TEXT_CHARS = 50

# Documents this short are always kept whole: page selection only pays off on
# long reports, and on short logs a false "irrelevant" would lose a borehole.
KEEP_ALL_MAX_PAGES = 2

# A page needs at least this many distinct keyword hits to count as a log page.
MIN_RELEVANCE = 2

# Terms that show up on borehole log sheets, in the languages of our sample data.
# Matched case-insensitively as substrings, so stems ("bohr", "sondag") cover
# several inflections. Keep them specific: generic words like "depth" on their
# own appear in report prose too, which is why we require MIN_RELEVANCE hits.
LOG_KEYWORDS = [
    # English
    "borehole", "bore hole", "drill hole", "drillhole", "hole no", "geological log",
    "depth", "elevation", "groundwater", "water level", "spt", "rqd", "core recovery",
    "lithology", "soil description", "sample",
    # German
    "bohrung", "bohrprofil", "schichtenverzeichnis", "teufe", "tiefe", "grundwasser",
    "kernbohrung", "probe",
    # Spanish / Portuguese
    "sondeo", "sondagem", "perforación", "profundidad", "profundidade", "nivel freático",
    "nível d'água", "cota", "muestra", "amostra",
    # French
    "forage", "sondage", "profondeur", "nappe", "échantillon",
    # Danish / Norwegian
    "boring", "boreprofil", "dybde", "grundvand", "grunnvann", "brønn",
]

# Labels that introduce a borehole ID, e.g.
#   "HOLE NO : BH_AB05S", "Borehole No.:   T01", "Borehole No. ( 1 )",
#   "SONDEO Nº 7", "Bohrung B 3".
# Breakdown of the pattern:
#   (?:...)              the label word(s)
#   \s*(?:no|nr|n[º°o])?\.?   optional "No"/"Nr"/"Nº"/"N°", optional dot
#   [\s:#(]*             separators: spaces (layout mode can insert many), ":", "#", "("
#   (?P<id>...)          the ID: a token of letters/digits/-/_, optionally followed by
#                        a second token after one space ("BH 2"). Dots are left out on
#                        purpose: headings like "BOREHOLE LOGS.-SKM04A" or dotted table
#                        of contents lines would otherwise be read as IDs.
# The regex alone is too permissive; _plausible_id() filters the candidates.
BOREHOLE_ID_RE = re.compile(
    r"\b(?:bore\s?hole|drill\s?hole|hole|bohrung|sondeo|sondagem|sondage|forage|boring|brønn)"
    r"\s*(?:no|nr|n[º°o])?\.?[ \t:#(]*"
    r"(?P<id>[A-Z0-9][A-Z0-9_-]*(?: [A-Z0-9_-]+)?)",
    re.IGNORECASE,
)

# "DEPTH OF BOREHOLE 8.0m" / "End of borehole 8m" match the label too; a bare
# number with a length unit is a depth, not an ID. Two cases: "8m" is captured
# whole as the candidate, while for "8.0m" the ID regex stops at the dot, so the
# unit has to be looked for in the text right after the match.
DEPTH_RE = re.compile(r"\d+\s*(?:m|ft)", re.IGNORECASE)
DEPTH_AFTER_RE = re.compile(r"\s*(?:[.,]\d+)?\s*(?:m|ft)\b", re.IGNORECASE)

# Borehole ID in an image file name, e.g. "BH-1.jpg", "B12_page2.png".
FILENAME_ID_RE = re.compile(r"^(?P<id>[A-Z]{1,4}[-_ ]?\d+[A-Z]?)", re.IGNORECASE)


class SourceKind(StrEnum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    # Some pages have a text layer, some don't (e.g. a typed report with scanned logs appended).
    MIXED_PDF = "mixed_pdf"
    IMAGE = "image"
    # A folder of images that together form one document (e.g. MEA03-jpg/).
    IMAGE_SET = "image_set"
    DOCX = "docx"


class Page(BaseModel):
    # File the page lives in. For image sets every page is its own file.
    file: Path
    # 0-based page index within `file` (always 0 for images and docx).
    index: int
    # None means the page has no usable text yet and must go through OCR.
    text: str | None = None
    # Number of distinct log keywords found; None until there is text to score.
    relevance: int | None = None
    borehole_id: str | None = None

    @computed_field
    @property
    def needs_ocr(self) -> bool:
        return self.text is None


class Document(BaseModel):
    """One borehole's worth of pages, ready for OCR and extraction."""

    # The original input (file or folder) this document was cut from.
    source: Path
    kind: SourceKind
    # None if we couldn't find an ID; extraction may still find one after OCR.
    borehole_id: str | None = None
    pages: list[Page]

    @computed_field
    @property
    def needs_ocr(self) -> bool:
        return any(p.needs_ocr for p in self.pages)


def discover(paths: Iterable[Path]) -> Iterator[tuple[Path, SourceKind, list[Page]]]:
    """Walk the input paths and yield (source, kind, pages) per logical document.

    Images sitting in the same folder are grouped into one IMAGE_SET; every
    other file is its own document. Unsupported files are logged and skipped.
    """
    for path in paths:
        if path.is_dir():
            yield from _discover_dir(path)
        else:
            if (loaded := _load_file(path)) is not None:
                yield path, *loaded


def triage(paths: Iterable[Path]) -> list[Document]:
    docs: list[Document] = []
    for source, kind, pages in discover(paths):
        kept = select_pages(pages)
        log.info("%s [%s]: kept %d/%d pages", source, kind, len(kept), len(pages))
        docs.extend(split_by_borehole(source, kind, kept))
    return docs


def select_pages(pages: list[Page]) -> list[Page]:
    """Drop pages that don't look like borehole logs (ADR-0003)."""
    for page in pages:
        if page.text is not None:
            page.relevance = score_relevance(page.text)

    if len(pages) <= KEEP_ALL_MAX_PAGES:
        return pages

    kept = [p for p in pages if p.needs_ocr or (p.relevance or 0) >= MIN_RELEVANCE]
    # If no text page scored high enough, the heuristic is probably wrong for
    # this document (unexpected language, odd layout). Sending everything on is
    # noisier but better than silently losing the whole document.
    if not any((p.relevance or 0) >= MIN_RELEVANCE for p in kept):
        return pages
    return kept


def score_relevance(text: str) -> int:
    lowered = text.lower()
    return sum(1 for kw in LOG_KEYWORDS if kw in lowered)


def find_borehole_id(text: str) -> str | None:
    for match in BOREHOLE_ID_RE.finditer(text):
        candidate = match.group("id").strip(" -_")
        if DEPTH_RE.fullmatch(candidate) or DEPTH_AFTER_RE.match(text, match.end()):
            continue
        if _plausible_id(candidate):
            return _normalise_id(candidate)
    return None


def _plausible_id(candidate: str) -> bool:
    """Reject regex matches that are words, not IDs ("Borehole Log", "hole diameter").

    Accepted: the first token has a digit ("T01", "BH_AB05S", "1"), or it's a
    short prefix followed by a numbered token ("BH 2"). Otherwise the label was
    followed by an ordinary word and a second token that happens to contain a
    digit ("Borehole Details 5") would slip through.
    """
    first, _, second = candidate.partition(" ")
    if any(c.isdigit() for c in first):
        return True
    return first.isalpha() and len(first) <= 4 and any(c.isdigit() for c in second)


def split_by_borehole(source: Path, kind: SourceKind, pages: list[Page]) -> list[Document]:
    """Group pages into one Document per borehole ID.

    Log sheets usually print the ID only in the header, and multi-sheet logs
    ("Sheet 2 of 3") or photo pages may not repeat it. So a page without an ID
    inherits the ID of the page before it. Pages before the first ID join the
    first borehole. Same-ID pages are merged even if not adjacent, which keeps
    split logs together.
    """
    for page in pages:
        if page.text is not None:
            page.borehole_id = find_borehole_id(page.text)
        elif kind == SourceKind.IMAGE_SET:
            # Scanned images have no text yet, but their file names often carry the ID.
            page.borehole_id = _id_from_filename(page.file)

    current: str | None = next((p.borehole_id for p in pages if p.borehole_id), None)
    groups: dict[str | None, list[Page]] = {}
    for page in pages:
        current = page.borehole_id or current
        groups.setdefault(current, []).append(page)

    return [
        Document(source=source, kind=kind, borehole_id=bid, pages=group)
        for bid, group in groups.items()
    ]


def _discover_dir(folder: Path) -> Iterator[tuple[Path, SourceKind, list[Page]]]:
    images: list[Path] = []
    for entry in sorted(folder.iterdir(), key=_natural_key):
        if entry.is_dir():
            yield from _discover_dir(entry)
        elif entry.suffix.lower() in IMAGE_SUFFIXES:
            images.append(entry)
        elif (loaded := _load_file(entry)) is not None:
            yield entry, *loaded
    if images:
        yield folder, SourceKind.IMAGE_SET, [Page(file=img, index=0) for img in images]


def _load_file(path: Path) -> tuple[SourceKind, list[Page]] | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix in IMAGE_SUFFIXES:
        return SourceKind.IMAGE, [Page(file=path, index=0)]
    if suffix == ".docx":
        return SourceKind.DOCX, [Page(file=path, index=0, text=_docx_text(path))]
    log.warning("skipping unsupported file %s", path)
    return None


def _load_pdf(path: Path) -> tuple[SourceKind, list[Page]]:
    import pypdf

    pages = []
    for i, pdf_page in enumerate(pypdf.PdfReader(path).pages):
        # Layout mode keeps labels and values on the same line
        # ("Borehole No.:      T01"); plain mode often splits them apart,
        # which breaks find_borehole_id.
        text = pdf_page.extract_text(extraction_mode="layout") or ""
        pages.append(Page(file=path, index=i, text=text if len(text.strip()) >= MIN_TEXT_CHARS else None))

    scanned = sum(p.needs_ocr for p in pages)
    if scanned == 0:
        kind = SourceKind.DIGITAL_PDF
    elif scanned == len(pages):
        kind = SourceKind.SCANNED_PDF
    else:
        kind = SourceKind.MIXED_PDF
    return kind, pages


def _docx_text(path: Path) -> str:
    import docx

    document = docx.Document(path)
    lines = [p.text for p in document.paragraphs]
    # Borehole logs in Word are usually tables, which `paragraphs` doesn't include.
    # One line per row, cells separated by " | ", mirrors the layout well enough
    # for keyword and ID matching.
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


def _id_from_filename(path: Path) -> str | None:
    match = FILENAME_ID_RE.match(path.stem)
    return _normalise_id(match.group("id")) if match else None


def _normalise_id(raw: str) -> str:
    # "bh 2", "BH-2" and "BH_2" should all end up as the same borehole.
    return re.sub(r"[\s_-]+", "-", raw.strip()).upper()


def _natural_key(path: Path) -> list:
    # Sort "Report01_4.png" before "Report01_10.png" (plain sort puts 10 first).
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]
