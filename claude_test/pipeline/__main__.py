"""Run with: uv run python -m pipeline <file.pdf>"""

import argparse
import json
import pathlib
import shutil
import sys
import time

from . import claude_cli, steps
from .naming import run_id, stamped
from .claude_cli import PipelineError, StepReport, Timer, Usage, log

DEFAULT_OUT = pathlib.Path(__file__).resolve().parent.parent / "out"


def print_report(reports: list[StepReport], total_wall: float) -> None:
    head = f"{'step':<22}{'model':<8}{'effort':<8}{'calls':>6}{'time':>9}{'input':>9}{'output':>9}{'cache r':>10}{'cache w':>10}{'total':>10}{'cost':>10}"
    print("\n" + head, file=sys.stderr)
    print("-" * len(head), file=sys.stderr)
    total = Usage()
    for r in reports:
        u = r.usage
        total.add(u)
        print(
            f"{r.name:<22}{r.model:<8}{r.effort:<8}{u.calls:>6}{r.wall_seconds:>8.1f}s"
            f"{u.input_tokens:>9}{u.output_tokens:>9}{u.cache_read_tokens:>10}{u.cache_create_tokens:>10}"
            f"{u.total_tokens:>10}{'$' + format(u.cost_usd, '.4f'):>10}",
            file=sys.stderr,
        )
    print("-" * len(head), file=sys.stderr)
    print(
        f"{'TOTAL':<22}{'':<8}{'':<8}{total.calls:>6}{total_wall:>8.1f}s"
        f"{total.input_tokens:>9}{total.output_tokens:>9}{total.cache_read_tokens:>10}{total.cache_create_tokens:>10}"
        f"{total.total_tokens:>10}{'$' + format(total.cost_usd, '.4f'):>10}",
        file=sys.stderr,
    )
    print(
        "(time = wall clock of the step, calls may run in parallel; cost as reported by the "
        "claude CLI; models actually used: "
        + ", ".join(sorted(total.models))
        + ")",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Borehole PDF -> database payloads via Claude.")
    parser.add_argument("pdf", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="output root (default: claude_test/out)")
    parser.add_argument("--chunk-size", type=int, default=10, help="pages per classification call in step 1")
    parser.add_argument("--workers", type=int, default=4, help="parallel claude calls per step")
    args = parser.parse_args()

    if shutil.which("pdftoppm") is None:
        # Claude's Read tool renders PDF pages with poppler; without it the models
        # only see the text layer or refuse to answer, which gave empty results.
        sys.exit("pdftoppm not found: install poppler first (macOS: brew install poppler)")

    pdf = args.pdf.resolve()
    out_dir = (args.out / pdf.stem).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    claude_cli.DEBUG_DIR = out_dir / "debug"
    log(f"run id: {run_id()}")
    log(f"input: {pdf} ({pdf.stat().st_size / 1024:.0f} KiB) -> output: {out_dir}")

    reports = [
        StepReport("1 filter pages", "haiku", "high"),
        StepReport("2 split boreholes", "haiku", "medium"),
        StepReport("3 extract", "sonnet", "high"),
        StepReport("4 transform to db", "haiku", "high"),
    ]
    r1, r2, r3, r4 = reports
    results: list[dict] = []
    t0 = time.monotonic()
    try:
        with Timer(r1):
            filtered = steps.filter_pages(pdf, out_dir, r1, args.chunk_size, args.workers)
        if filtered is not None:
            pages_pdf, page_hints = filtered
            with Timer(r2):
                files = steps.split_boreholes(pages_pdf, out_dir, r2, page_hints)
            with Timer(r3):
                extracted = steps.extract_boreholes(files, out_dir, r3, args.workers)
            with Timer(r4):
                results = steps.transform_boreholes(extracted, out_dir, r4, args.workers)
        else:
            log("no borehole log pages found, nothing to do")
    except PipelineError as e:
        log(f"pipeline failed: {e}")
        return 1
    finally:
        stamped(out_dir / "report.json").write_text(
            json.dumps([r.to_dict() for r in reports], indent=2)
        )
        print_report(reports, time.monotonic() - t0)

    result_file = stamped(out_dir / "result.json")
    result_file.write_text(
        json.dumps({"source": str(pdf), "boreholes": results}, indent=2, ensure_ascii=False)
    )
    log(f"result: {result_file} ({len(results)} borehole(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
