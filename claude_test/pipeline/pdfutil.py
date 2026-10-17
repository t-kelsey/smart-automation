import pathlib
from collections.abc import Iterable

from pypdf import PdfReader, PdfWriter


def page_count(pdf: pathlib.Path) -> int:
    return len(PdfReader(pdf).pages)


def write_pages(src: pathlib.Path, pages: Iterable[int], dest: pathlib.Path) -> None:
    """Write the given 1-based pages of `src` (in the given order) to `dest`."""
    reader = PdfReader(src)
    writer = PdfWriter()
    for p in pages:
        writer.add_page(reader.pages[p - 1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        writer.write(f)
