"""Pipeline: OCR -> translate -> extract -> split into per-borehole JSON (ADR-0007).

Run from bem/ (the modules import each other without a package prefix):
    python main.py <file-or-dir>... [--api http://localhost:4000/api/boreholes] [--dry-run]
"""

import argparse
import logging
from pathlib import Path

import requests

from ocr import ocr_file
from schema import Borehole
from translation_and_extraction import extract, translate
from triage import split

OUTPUT_DIR = Path(__file__).parent / "output"
OCR_DIR = OUTPUT_DIR / "ocr"
RECORD_DIR = OUTPUT_DIR / "records"
INPUT_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx"}

log = logging.getLogger(__name__)


def input_files(paths: list[Path]):
    for path in paths:
        if path.is_dir():
            yield from sorted(f for f in path.rglob("*") if f.suffix.lower() in INPUT_SUFFIXES)
        elif path.suffix.lower() in INPUT_SUFFIXES:
            yield path
        else:
            log.warning("skipping unsupported file %s", path)


def process(path: Path, api: str | None) -> list[Borehole]:
    """Run one input through every stage. Writes JSON records, and POSTs them if api is set."""
    md_path = ocr_file(path, OCR_DIR)
    markdown = extract(translate(md_path.read_text(encoding="utf-8")))
    boreholes = split(path.name, markdown)

    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    for borehole in boreholes:
        name = f"{md_path.stem}_{borehole.borehole_id or 'unknown'}.json"
        (RECORD_DIR / name).write_text(borehole.model_dump_json(indent=2), encoding="utf-8")
        if api:
            requests.post(api, json=borehole.model_dump(mode="json"), timeout=30).raise_for_status()
    return boreholes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--api", default="http://localhost:4000/api/boreholes")
    parser.add_argument("--dry-run", action="store_true", help="write JSON only, don't POST")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    api = None if args.dry_run else args.api
    for path in input_files(args.paths):
        for borehole in process(path, api):
            print(f"{path.name}: borehole={borehole.borehole_id} chars={len(borehole.raw_markdown)}")


if __name__ == "__main__":
    main()
