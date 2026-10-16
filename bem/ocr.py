"""OCR for scanned and handwritten pages.

Open problem (ADR-0001): this is a basic Tesseract baseline that will be replaced
once we choose a proper OCR approach. Expect poor results on handwriting and tables.
"""

from .triage import Document, Page


def ocr(doc: Document) -> Document:
    import pytesseract

    for page in doc.pages:
        if page.needs_ocr:
            page.text = pytesseract.image_to_string(_image(page))
    return doc


def _image(page: Page):
    if page.file.suffix.lower() == ".pdf":
        from pdf2image import convert_from_path

        # pdf2image pages are 1-based.
        n = page.index + 1
        return convert_from_path(page.file, dpi=300, first_page=n, last_page=n)[0]
    from PIL import Image

    return Image.open(page.file)
