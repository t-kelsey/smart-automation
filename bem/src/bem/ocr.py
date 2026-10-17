"""OCR: turn each input file into markdown with Docling (ADR-0007, ADR-0008).

Every page is OCR'd, including digital PDFs, because the text layer loses the
table structure that borehole logs depend on. Output is one markdown file per input.
"""

import gc
from pathlib import Path

# Docling is heavy, so it's imported on first use. That keeps importing this module
# (for example from test.py) cheap until OCR actually runs.
_converter = None


def _get_converter(ocr_engine: str = "easyocr"):
    global _converter

    if _converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            EasyOcrOptions,
            PdfPipelineOptions,
            #PaddleOcrOptions,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        if ocr_engine.lower() == "easyocr":
            ocr_options = EasyOcrOptions(force_full_page_ocr=True)

        # elif ocr_engine.lower() == "paddleocr":
        #     ocr_options = PaddleOcrOptions(force_full_page_ocr=True)

        else:
            raise ValueError(f"Unsupported OCR engine: {ocr_engine}")

        options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
            ocr_options=ocr_options,
        )

        pdf_format = PdfFormatOption(pipeline_options=options)

        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_format,
                InputFormat.IMAGE: pdf_format,
            }
        )

    return _converter


def ocr_file(path: Path) -> str:
    """OCR one file to markdown and return the path of the markdown file."""
    # Prefix with the folder name: different inputs can share a file name (e.g. Report01.pdf).
    markdown = _get_converter().convert(path).document.export_to_markdown()
    return markdown


def unload_ocr() -> None:
    """Drop the Docling converter and free its (GPU) memory, so the extraction model can use it.

    The next ocr_file() call loads the models again.
    """
    global _converter
    _converter = None
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
