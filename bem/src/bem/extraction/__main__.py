"""Run the extraction on ONE OCR text file, with progress output.

    uv run --project bem python -m bem.extraction output/translate/AF01.md
    uv run --project bem python -m bem.extraction output/translate/AF01.md --out-dir results --markdown

Input : a text/markdown file (translated OCR output of one borehole report)
Output: <out-dir>/<name>.json   record + status + issues + provenance   (always)
        <out-dir>/<name>.md     record in template format               (only with --markdown)
The default out-dir is bem/output/extraction (inside the repo, wherever you run the command from).
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

from .config import load_prompt, load_settings
from .extract import extract_record, make_client
from .render import render
from .validate import check_all, status

# this file lives in bem/src/bem/extraction/, so parents[3] is bem/  ->  bem/output/extraction
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[3] / "output" / "extraction"


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
    ap.add_argument("input", type=Path, help="translated OCR text/markdown file")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output folder (default: bem/output/extraction)")
    ap.add_argument("--markdown", action="store_true", help="also write the record in template Markdown format")
    ap.add_argument("--model", help="default: config/settings.toml")
    ap.add_argument("--base-url", help="default: config/settings.toml")
    ap.add_argument("--prompt-file", type=Path, help="system prompt file (default: config/system_prompt.md)")
    args = ap.parse_args()
    cfg = load_settings()["model"]
    args.model = args.model or cfg["name"]
    args.base_url = args.base_url or cfg["base_url"]
    prompt = load_prompt(args.prompt_file)

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
            b = extract_record(text, make_client(args.base_url), args.model, system_prompt=prompt)
    except Exception as e:  # noqa: BLE001
        sys.exit(
            f"\nExtraction failed: {e}\n"
            "Check that Ollama is running ('ollama ps') and the model is pulled ('ollama list')."
        )
    print(f"      done in {sp.elapsed:.1f}s: {len(b.layers)} layers found")

    # 3 - validate
    b.layers.sort(key=lambda l: l.depth_from_m)
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
        "record": b.to_pipeline().model_copy(update={"source_file": args.input.name, "raw_markdown": text}).to_api_dict(),
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
