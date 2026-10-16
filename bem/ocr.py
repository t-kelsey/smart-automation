"""OCR for scanned and handwritten documents.

Open problem (ADR-0001): this is a basic Tesseract baseline that will be replaced
once we choose a proper OCR approach. Expect poor results on handwriting and tables.
"""

from .triage import Document, Kind


def ocr(doc: Document) -> Document:
    if not doc.needs_ocr:
        return doc
    import pytesseract

    doc.pages = [pytesseract.image_to_string(img) for img in _images(doc)]
    return doc


def _images(doc: Document):
    if doc.kind == Kind.SCANNED_PDF:
        from pdf2image import convert_from_path

        return convert_from_path(doc.path, dpi=300)
    from PIL import Image

    return [Image.open(doc.path)]
