"""Run the pipeline: triage -> OCR -> translation/extraction -> Elixir API (ADR-0001).

Usage: python -m bem.main <file-or-dir>... [--api http://localhost:4000/api/boreholes] [--dry-run]
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .ocr import ocr
from .translation_and_extraction import extract
from .triage import Kind, triage


def iter_files(paths: list[Path]):
    for p in paths:
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.is_file())
        else:
            yield p


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--api", default="http://localhost:4000/api/boreholes")
    parser.add_argument("--dry-run", action="store_true", help="print records instead of POSTing")
    args = parser.parse_args()

    for path in iter_files(args.paths):
        doc = triage(path)
        print(f"[{doc.kind.value}] {path}")
        if doc.kind == Kind.UNSUPPORTED:
            continue
        for borehole in extract(ocr(doc)):
            record = asdict(borehole)
            if args.dry_run:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                import requests

                requests.post(args.api, json=record, timeout=30).raise_for_status()


if __name__ == "__main__":
    main()
