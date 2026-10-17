"""Run the extraction on ONE OCR text file, with progress output.

    uv run --project bem python -m bem.extraction test.txt
    uv run --project bem python -m bem.extraction test.txt --out-dir results --markdown

Input : a plain-text file (OCR output of one borehole report)
Output: <out-dir>/<name>.json   record + status + issues + provenance   (always)
        <out-dir>/<name>.md     record in template format               (only with --markdown)
The default out-dir is ./output, relative to the folder you run the command in.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .extract import extract, make_client
from .render import render
from .validate import check_all, status


class Spinner:
    """Shows a spinner and the elapsed seconds while a slow step runs."""

    def __init__(self, message: str) -> None:
        self.message = message
        self.elapsed = 0.0
        self._start = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        frames = "|/-\\"
        i = 0
        while not self._stop.is_set():
            secs = time.time() - self._start
            sys.stdout.write(f"\r      {frames[i % 4]} {self.message} ... {secs:4.0f}s")
            sys.stdout.flush()
            i += 1
            time.sleep(0.2)

    def __enter__(self) -> "Spinner":
        self._start = time.time()
        self._thread.start()
        return self

    def __exit__(self, *exc) -> bool:
        self._stop.set()
        self._thread.join()
        self.elapsed = time.time() - self._start
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract one borehole record from an OCR text file.")
    ap.add_argument("input", type=Path, help="OCR text file (.txt)")
    ap.add_argument("--out-dir", type=Path, default=Path("output"), help="output folder (default: ./output)")
    ap.add_argument("--markdown", action="store_true", help="also write the record in template Markdown format")
    ap.add_argument("--model", default="qwen3.5:2b")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    args = ap.parse_args()

    if not args.input.is_file():
        sys.exit(f"Input file not found: {args.input}")

    out_dir = args.out_dir.resolve()
    json_path = out_dir / f"{args.input.stem}.json"
    md_path = out_dir / f"{args.input.stem}.md"

    print(f"Input : {args.input.resolve()}")
    print(f"Model : {args.model}  ({args.base_url})")
    print(f"Output: {json_path}")
    if args.markdown:
        print(f"        {md_path}")
    print()

    # 1 - read
    text = args.input.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[1/4] Read input: {len(text):,} characters")

    # 2 - extract (the slow step)
    print(f"[2/4] Extracting with {args.model} (the first call also loads the model)")
    try:
        with Spinner("waiting for the model") as sp:
            b = extract(text, make_client(args.base_url), args.model)
    except Exception as e:  # noqa: BLE001
        sys.exit(
            f"\nExtraction failed: {e}\n"
            "Check that Ollama is running ('ollama ps') and the model is pulled ('ollama list')."
        )
    print(f"      done in {sp.elapsed:.1f}s: {len(b.schichten)} layers found")

    # 3 - validate
    b.schichten.sort(key=lambda l: l.von_m)
    issues = check_all(b, text)
    st = status(issues)
    print(f"[3/4] Validated: status {st.upper()}, {len(issues)} issue(s)")
    for i in issues:
        print(f"      - [{i.level}] {i.field}: {i.message}")

    # 4 - write
    result = {
        "source_file": args.input.name,
        "model": args.model,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": st,
        "issues": [asdict(i) for i in issues],
        "record": b.model_dump(mode="json"),
    }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    written = [json_path]
    if args.markdown:
        md_path.write_text(render(b), encoding="utf-8")
        written.append(md_path)
    print(f"[4/4] Written: {', '.join(p.name for p in written)}")
    print(f"\nDone. Results are in {out_dir}")


if __name__ == "__main__":
    main()
