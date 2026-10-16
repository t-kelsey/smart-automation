"""Run the pipeline: triage -> OCR -> translation/extraction -> Elixir API (ADR-0001).

Usage: python -m bem.main <file-or-dir>... [--api http://localhost:4000/api/boreholes] [--dry-run]
"""

import argparse
import logging
import json
from dataclasses import asdict
from pathlib import Path

from .ocr import ocr
from .translation_and_extraction import extract
from .triage import triage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--api", default="http://localhost:4000/api/boreholes")
    parser.add_argument("--dry-run", action="store_true", help="print records instead of POSTing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for doc in triage(args.paths):
        print(f"[{doc.kind}] {doc.source.name} borehole={doc.borehole_id} pages={len(doc.pages)}")
        for borehole in extract(ocr(doc)):
            record = asdict(borehole)
            if args.dry_run:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                import requests

                requests.post(args.api, json=record, timeout=30).raise_for_status()


if __name__ == "__main__":
    main()
