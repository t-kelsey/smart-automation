"""Run with: uv run python -m pipeline <file.pdf>"""

import argparse
import contextlib
import json
import pathlib
import shutil
import sys
import tempfile
import threading
import time

from .ai import PipelineError, StepReport, Timer, Usage, backend_names, get_ai, log
from .config import PipelineConfig
from .naming import run_id, stamped
from .output import Recorder, Tracker, dump_json, persist_enabled
from .steps.extract import extract_boreholes
from .steps.filter import filter_pages
from .steps.split import split_boreholes
from .steps.translate import transform_boreholes

STAGES = ("filter", "split", "extract", "transform")
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


def run_pipeline(
    pdf: pathlib.Path,
    out_dir: pathlib.Path | None = None,
    chunk_size: int = 10,
    workers: int = 4,
    config: PipelineConfig | None = None,
    tracker: Tracker | None = None,
    stop: threading.Event | None = None,
) -> tuple[list[dict], list[StepReport], float]:
    """Run all four steps on one PDF; every stage (and borehole) reports its start, result or failure
    to `tracker`. Setting `stop` cancels the run with PipelineStopped at the next stage, borehole or
    AI call.

    The intermediate PDFs the model reads live in `out_dir`. With BEM_ENV=prod (or no `out_dir`)
    that is a temporary directory that is removed afterwards, and no JSON is written locally.
    Returns (results, step reports, wall seconds); raises PipelineError if a step fails.
    """
    with contextlib.ExitStack() as stack:
        if out_dir is None or not persist_enabled():
            out_dir = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="bem-")))
        return _run(pdf, out_dir, chunk_size, workers, config or PipelineConfig(), Recorder(tracker), stop)


def _run(
    pdf: pathlib.Path,
    out_dir: pathlib.Path,
    chunk_size: int,
    workers: int,
    c: PipelineConfig,
    recorder: Recorder,
    stop: threading.Event | None,
) -> tuple[list[dict], list[StepReport], float]:
    reports = [
        StepReport("1 filter pages", c.filter.model, c.filter.effort, stop=stop),
        StepReport("2 split boreholes", c.split.model, c.split.effort, stop=stop),
        StepReport("3 extract", c.extract.model, c.extract.effort, stop=stop),
        StepReport("4 transform to db", c.transform.model, c.transform.effort, stop=stop),
    ]
    r1, r2, r3, r4 = reports
    results: list[dict] = []
    t0 = time.monotonic()
    stage = "filter"
    try:
        with Timer(r1):
            filtered = filter_pages(pdf, out_dir, r1, chunk_size, workers, recorder)
        if filtered is not None:
            pages_pdf, page_hints = filtered
            stage = "split"
            with Timer(r2):
                files = split_boreholes(pages_pdf, out_dir, r2, page_hints, recorder)
            stage = "extract"
            with Timer(r3):
                extracted = extract_boreholes(files, out_dir, r3, workers, recorder)
            stage = "transform"
            with Timer(r4):
                results = transform_boreholes(extracted, out_dir, r4, workers, recorder)
        else:
            log("no borehole log pages found, nothing to do")
    except Exception as e:  # extract/transform record their own failures per borehole
        recorder.record_failure(stage, e, report=dict(zip(STAGES, reports))[stage])
        raise
    finally:
        wall = time.monotonic() - t0
        dump_json(stamped(out_dir / "report.json"), [r.to_dict() for r in reports])
        print_report(reports, wall)
    return results, reports, wall


def main() -> int:
    parser = argparse.ArgumentParser(description="Borehole PDF -> database payloads via Claude.")
    parser.add_argument("pdf", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="output root (default: claude_test/out)")
    parser.add_argument("--chunk-size", type=int, default=10, help="pages per classification call in step 1")
    parser.add_argument("--workers", type=int, default=4, help="parallel claude calls per step")
    parser.add_argument("--ai", choices=backend_names(), help="AI backend (default: env BEM_AI or openrouter)")
    args = parser.parse_args()

    if shutil.which("pdftoppm") is None:
        # Claude's Read tool renders PDF pages with poppler; without it the models
        # only see the text layer or refuse to answer, which gave empty results.
        sys.exit("pdftoppm not found: install poppler first (macOS: brew install poppler)")

    pdf = args.pdf.resolve()
    out_dir = (args.out / pdf.stem).resolve()
    get_ai(args.ai).debug_dir = out_dir / "debug" if persist_enabled() else None
    log(f"run id: {run_id()}")
    log(f"input: {pdf} ({pdf.stat().st_size / 1024:.0f} KiB) -> output: {out_dir}")

    try:
        results, _, _ = run_pipeline(pdf, out_dir, args.chunk_size, args.workers)
    except PipelineError as e:
        log(f"pipeline failed: {e}")
        return 1

    result = {"source": str(pdf), "boreholes": results}
    if persist_enabled():
        result_file = stamped(out_dir / "result.json")
        dump_json(result_file, result)
        log(f"result: {result_file} ({len(results)} borehole(s))")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
