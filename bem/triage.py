"""Triage: classify raw input files and decide which ones need OCR (ADR-0001)."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
# A PDF page with fewer extractable characters than this is treated as scanned.
MIN_TEXT_CHARS = 50


class Kind(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"
    DOCX = "docx"
    UNSUPPORTED = "unsupported"


@dataclass
class Document:
    path: Path
    kind: Kind
    # Pages are text for digital sources; empty until OCR fills them for scanned ones.
    pages: list[str] = field(default_factory=list)

    @property
    def needs_ocr(self) -> bool:
        return self.kind in (Kind.SCANNED_PDF, Kind.IMAGE)


def triage(path: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = _pdf_text(path)
        if sum(len(p.strip()) for p in pages) >= MIN_TEXT_CHARS * max(len(pages), 1):
            return Document(path, Kind.DIGITAL_PDF, pages)
        return Document(path, Kind.SCANNED_PDF)
    if suffix in IMAGE_SUFFIXES:
        return Document(path, Kind.IMAGE)
    if suffix == ".docx":
        return Document(path, Kind.DOCX, [_docx_text(path)])
    return Document(path, Kind.UNSUPPORTED)


def _pdf_text(path: Path) -> list[str]:
    import pypdf

    return [page.extract_text() or "" for page in pypdf.PdfReader(path).pages]


def _docx_text(path: Path) -> str:
    import docx

    return "\n".join(p.text for p in docx.Document(path).paragraphs)
