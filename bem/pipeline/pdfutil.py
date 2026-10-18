import pathlib
import shutil
import subprocess
import tempfile
import zipfile
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


def is_docx(path: pathlib.Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return "word/document.xml" in z.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def docx_to_pdf(docx: pathlib.Path, dest: pathlib.Path) -> None:
    """Convert a Word document to a PDF at `dest` with headless LibreOffice.

    Raises ValueError if LibreOffice is missing or cannot convert the file.
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise ValueError("LibreOffice (soffice) not found, install it to read Word documents")
    with tempfile.TemporaryDirectory(prefix="bem-docx-") as tmp:
        tmp = pathlib.Path(tmp)
        src = tmp / "in.docx"  # fixed name: the output is in.pdf whatever the original was called
        shutil.copyfile(docx, src)
        cmd = [
            soffice,
            f"-env:UserInstallation={(tmp / 'profile').as_uri()}",  # private profile: no lock clashes between workers
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp / "out"),
            str(src),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise ValueError(f"LibreOffice could not convert the document: {e}") from e
        result = tmp / "out" / "in.pdf"
        if not result.exists():
            raise ValueError("LibreOffice produced no PDF")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(result, dest)
