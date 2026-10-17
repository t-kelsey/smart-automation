"""Run the borehole pipeline: OCR -> translation and labeling -> triage -> extraction -> output.

Usage:
    python -m bem.main <file-or-dir>... [--to api|json|print] [--api-url URL] [--out-dir DIR]
"""

import argparse
import logging
from pathlib import Path

from .ocr import ocr_file
from .translation_and_labeling.translation_and_labeling import translate
from .triage import split
from .extraction import extract
from .output import make_sink

log = logging.getLogger("bem")

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx"}
OUTPUT_DIR = Path(__file__).parent / "output"


def collect_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories into the supported files they contain."""
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
        else:
            files.append(path)
    return files


def save_stage(stage: str, path: Path, content: str, suffix: str = ".md") -> None:
    """Write one stage's output to output/<stage>/<input stem><suffix> (debug only)."""
    out_dir = OUTPUT_DIR / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{path.stem}{suffix}").write_text(content, encoding="utf-8")


def process_file(path: Path, sink, debug: bool) -> int:
    """Push every borehole found in one input file through the pipeline. Returns the count.

    With debug, the output of OCR, translation, triage and extraction is saved under output/.
    """
    document = ocr(path)              # any format -> TextDocument (digital text layer or OCR'd pages)
    if debug:
        save_stage("ocr", path, document)
    document, _ = translate(document)  # local terms -> English, keywords labeled
    if debug:
        save_stage("translate", path, document)
    count = 0
    for i, section in enumerate(split(path.name, document)):  # one Borehole per borehole ID
        if debug:
            save_stage("triage", path, section.model_dump_json(indent=2), f"__{i}.json")
        record = extract(section)     # Borehole -> Borehole (JSON-serialisable)
        if debug:
            save_stage("extract", path, record.model_dump_json(indent=2), f"__{i}.json")
        sink(record)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--to", choices=["api", "json", "print"], default="print")
    parser.add_argument("--api-url", default="http://localhost:4000/api/boreholes")
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    parser.add_argument("--debug", action="store_true", help="save intermediate stages to output/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    failed = []
    with make_sink(args.to, api_url=args.api_url, out_dir=args.out_dir) as sink:
        for path in collect_inputs(args.inputs):
            try:
                count = process_file(path, sink, args.debug)
                log.info("%s: %d borehole(s)", path.name, count)
            except Exception:
                log.exception("failed: %s", path)
                failed.append(path)

    if failed:
        raise SystemExit(f"{len(failed)} file(s) failed: {', '.join(str(p) for p in failed)}")


if __name__ == "__main__":
    main()
