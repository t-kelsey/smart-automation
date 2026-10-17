"""OCR: turn each input file into markdown with Docling (ADR-0007, ADR-0008).

Every page is OCR'd, including digital PDFs, because the text layer loses the
table structure that borehole logs depend on. Output is one markdown file per input.
"""

from pathlib import Path

# Docling is heavy, so it's imported on first use. That keeps importing this module
# (for example from test.py) cheap until OCR actually runs.
_converter = None


def _get_converter():
    global _converter
    if _converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # force_full_page_ocr ignores any embedded text layer and reads every page from
        # its image. Table structure recognition stays on: it's what makes the markdown
        # tables usable downstream.
        options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
            ocr_options=EasyOcrOptions(force_full_page_ocr=True), # type: ignore
        )
        pdf_format = PdfFormatOption(pipeline_options=options)
        # Images go through the same pipeline as PDFs, so they get the same OCR settings.
        _converter = DocumentConverter(
            format_options={InputFormat.PDF: pdf_format, InputFormat.IMAGE: pdf_format}
        )
    return _converter


def ocr_file(path: Path) -> str:
    """OCR one file to markdown and return the path of the markdown file."""
    # Prefix with the folder name: different inputs can share a file name (e.g. Report01.pdf).
    markdown = _get_converter().convert(path).document.export_to_markdown()
    return markdown
