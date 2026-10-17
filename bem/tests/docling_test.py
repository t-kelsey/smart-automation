
#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert documents to Markdown using Docling."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the input document (e.g. report.pdf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Save Markdown to this file instead of printing to the terminal.",
    )

    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")

    try:
        converter = DocumentConverter()
        result = converter.convert(str(args.input))
        markdown = result.document.export_to_markdown()

        if args.output:
            args.output.write_text(markdown, encoding="utf-8")
            print(f"Markdown saved to: {args.output}", file=sys.stderr)
        else:
            print(markdown)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
