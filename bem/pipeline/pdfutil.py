import pathlib
from collections.abc import Iterable

from PIL import Image, ImageSequence
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


def image_to_pdf(image: pathlib.Path, dest: pathlib.Path) -> None:
    """Convert a raster image (PNG, JPEG, TIFF; every frame of a multi-page TIFF) to a PDF at `dest`.

    Raises ValueError if `image` is not a readable image.
    """
    try:
        with Image.open(image) as im:
            pages = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
    except (OSError, Image.DecompressionBombError) as e:
        raise ValueError(f"not a readable image: {e}") from e
    dpi = float(im.info.get("dpi", (200, 200))[0] or 200)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(dest, "PDF", save_all=True, append_images=pages[1:], resolution=dpi)
