"""Run the borehole pipeline: OCR -> translation and labeling -> triage -> extraction -> output.

Usage:
    python -m bem.main <file-or-dir>... [--to api|json|print] [--api-url URL] [--out-dir DIR]
"""

import argparse
import logging
from pathlib import Path

from .extraction import extract
from .ocr import ocr
from .output import make_sink
from .translation_and_labeling.translation_and_labeling import translate
from .triage import triage

log = logging.getLogger("bem")

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx"}


def collect_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories into the supported files they contain."""
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
        else:
            files.append(path)
    return files


def process_file(path: Path, sink) -> int:
    """Push every borehole found in one input file through the pipeline. Returns the count."""
    document = ocr(path)              # any format -> TextDocument (digital text layer or OCR'd pages)
    document = translate(document)    # local terms -> English, keywords labeled
    count = 0
    for section in triage(document):  # one BoreholeText per borehole, irrelevant parts dropped
        sink(extract(section))        # BoreholeText -> Borehole (JSON-serialisable)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--to", choices=["api", "json", "print"], default="print")
    parser.add_argument("--api-url", default="http://localhost:4000/api/boreholes")
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    failed = []
    with make_sink(args.to, api_url=args.api_url, out_dir=args.out_dir) as sink:
        for path in collect_inputs(args.inputs):
            try:
                count = process_file(path, sink)
                log.info("%s: %d borehole(s)", path.name, count)
            except Exception:
                log.exception("failed: %s", path)
                failed.append(path)

    if failed:
        raise SystemExit(f"{len(failed)} file(s) failed: {', '.join(str(p) for p in failed)}")


if __name__ == "__main__":
    main()
