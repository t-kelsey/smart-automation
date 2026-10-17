"""Run with: uv run python -m pipeline <file.pdf>"""

import argparse
import contextlib
import json
import pathlib
import shutil
import sys
import tempfile
import time

from .ai import AI, PROVIDER_BACKENDS, PipelineError, StepReport, Timer, Usage, backend_names, get_ai, log, new_ai
from .config import PipelineConfig, default_chunk_size, resolve_models
from .naming import run_id, stamped
from .output import OnStage, Recorder, dump_json, persist_enabled
from .steps.extract import extract_boreholes
from .steps.filter import filter_pages
from .steps.split import split_boreholes
from .steps.translate import transform_boreholes

DEFAULT_OUT = pathlib.Path(__file__).resolve().parent.parent / "out"


def print_report(reports: list[StepReport], total_wall: float) -> None:
    head = f"{'step':<22}{'model':<14}{'effort':<8}{'calls':>6}{'time':>9}{'input':>9}{'output':>9}{'cache r':>10}{'cache w':>10}{'total':>10}{'cost':>10}"
    print("\n" + head, file=sys.stderr)
    print("-" * len(head), file=sys.stderr)
    total = Usage()
    for r in reports:
        u = r.usage
        total.add(u)
        print(
            f"{r.name:<22}{r.model:<14}{r.effort:<8}{u.calls:>6}{r.wall_seconds:>8.1f}s"
            f"{u.input_tokens:>9}{u.output_tokens:>9}{u.cache_read_tokens:>10}{u.cache_create_tokens:>10}"
            f"{u.total_tokens:>10}{'$' + format(u.cost_usd, '.4f'):>10}",
            file=sys.stderr,
        )
    print("-" * len(head), file=sys.stderr)
    print(
        f"{'TOTAL':<22}{'':<14}{'':<8}{total.calls:>6}{total_wall:>8.1f}s"
        f"{total.input_tokens:>9}{total.output_tokens:>9}{total.cache_read_tokens:>10}{total.cache_create_tokens:>10}"
        f"{total.total_tokens:>10}{'$' + format(total.cost_usd, '.4f'):>10}",
        file=sys.stderr,
    )
    print(
        "(time = wall clock of the step, calls may run in parallel; cost as reported by the "
        "provider, 0 for local models; models actually used: "
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
    on_stage: OnStage | None = None,
    ai: AI | None = None,
) -> tuple[list[dict], list[StepReport], float]:
    """Run all four steps on one PDF; every step hands its output to `on_stage(stage, position, data, files)`.

    The intermediate PDFs the model reads live in `out_dir`. With BEM_ENV=prod (or no `out_dir`)
    that is a temporary directory that is removed afterwards, and no JSON is written locally.
    `ai` is the backend for this run; default: the process-wide one for provider "claude" (`--ai`/BEM_AI),
    a fresh local backend for provider "local".
    Returns (results, step reports, wall seconds); raises PipelineError if a step fails.
    """
    config = config or PipelineConfig()
    if ai is None:
        ai = get_ai() if config.provider == "claude" else new_ai(PROVIDER_BACKENDS[config.provider])
    with contextlib.ExitStack() as stack:
        if out_dir is None or not persist_enabled():
            out_dir = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="bem-")))
        return _run(pdf, out_dir, chunk_size, workers, config, Recorder(on_stage), ai)


def _run(
    pdf: pathlib.Path, out_dir: pathlib.Path, chunk_size: int, workers: int, c: PipelineConfig,
    recorder: Recorder,
    ai: AI,
) -> tuple[list[dict], list[StepReport], float]:
    m = resolve_models(c)
    reports = [
        StepReport("1 filter pages", m["filter"].model, m["filter"].effort, c.provider),
        StepReport("2 split boreholes", m["split"].model, m["split"].effort, c.provider),
        StepReport("3 extract", m["extract"].model, m["extract"].effort, c.provider),
        StepReport("4 transform to db", m["transform"].model, m["transform"].effort, c.provider),
    ]
    r1, r2, r3, r4 = reports
    results: list[dict] = []
    t0 = time.monotonic()
    try:
        with Timer(r1):
            filtered = filter_pages(pdf, out_dir, r1, chunk_size, workers, recorder, ai)
        if filtered is not None:
            pages_pdf, page_hints = filtered
            with Timer(r2):
                files = split_boreholes(pages_pdf, out_dir, r2, page_hints, recorder, ai)
            with Timer(r3):
                extracted = extract_boreholes(files, out_dir, r3, workers, recorder, ai)
            with Timer(r4):
                results = transform_boreholes(extracted, out_dir, r4, workers, recorder, ai)
        else:
            log("no borehole log pages found, nothing to do")
    finally:
        wall = time.monotonic() - t0
        dump_json(stamped(out_dir / "report.json"), [r.to_dict() for r in reports])
        print_report(reports, wall)
    return results, reports, wall


def main() -> int:
    parser = argparse.ArgumentParser(description="Borehole PDF -> database payloads via Claude.")
    parser.add_argument("pdf", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="output root (default: claude_test/out)")
    parser.add_argument("--chunk-size", type=int, help="pages per classification call in step 1 (default: 10, local: 2)")
    parser.add_argument("--workers", type=int, default=4, help="parallel claude calls per step")
    parser.add_argument("--ai", choices=backend_names(), help="AI backend (default: env BEM_AI or claude_cli; local = Ollama vision model)")
    args = parser.parse_args()

    if shutil.which("pdftoppm") is None:
        # Claude's Read tool renders PDF pages with poppler; without it the models
        # only see the text layer or refuse to answer, which gave empty results.
        sys.exit("pdftoppm not found: install poppler first (macOS: brew install poppler)")

    pdf = args.pdf.resolve()
    out_dir = (args.out / pdf.stem).resolve()
    ai = get_ai(args.ai)
    ai.debug_dir = out_dir / "debug" if persist_enabled() else None
    config = PipelineConfig(provider="claude" if ai.reads_files else "local")
    log(f"run id: {run_id()}")
    log(f"input: {pdf} ({pdf.stat().st_size / 1024:.0f} KiB) -> output: {out_dir}")

    try:
        results, _, _ = run_pipeline(
            pdf, out_dir, args.chunk_size or default_chunk_size(config.provider), args.workers, config, ai=ai
        )
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
