"""The four pipeline steps. Each writes its intermediate output below `out_dir`."""

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from .. import pdfutil, schemas
from ..naming import base, stamped
from ..output import Recorder, dump_json
from ..ai import PipelineError, StepReport, get_ai, log

MAX_READ_PAGES = 20  # the Read tool renders at most 20 PDF pages per call


def _dump(path: pathlib.Path, data) -> None:
    dump_json(stamped(path), data)


# --------------------------------------------------------------------------
# Step 1: keep only real borehole log pages            (haiku, high effort)
# --------------------------------------------------------------------------

FILTER_PROMPT = """Read every page of the PDF at {path} ({n} pages, use the Read tool's
`pages` parameter, e.g. "1-{n}"). Classify each page.

Keep a page (is_borehole_log=true) only if it is a real borehole log sheet: a drilling
log / core log / Bohrprofil / Schichtenverzeichnis / sondage / columna estratigrafica,
i.e. a graphic or tabular profile with depth and layer descriptions for one borehole.
Continuation sheets of a log also count.

Reject everything else: cover pages, tables of contents, running report text, maps and
site plans, cross sections, legends/standards pages, lab or test result tables, photos,
blank pages. When unsure whether a page is part of a log, keep it.

Return one entry per page, numbered 1..{n} within this file. Give your final answer
only through the structured output, not as prose."""


def filter_pages(
    pdf: pathlib.Path,
    out_dir: pathlib.Path,
    report: StepReport,
    chunk_size: int,
    workers: int,
    recorder: Recorder = Recorder(),
) -> tuple[pathlib.Path, list[str]] | None:
    """Returns (PDF with only borehole log pages, one hint per kept page), or None if there are none."""
    recorder.start("filter", report)
    step_dir = out_dir / "01_filter"
    total = pdfutil.page_count(pdf)
    log(f"step 1: {total} pages, classifying in chunks of {chunk_size}")

    chunks = []
    for i, start in enumerate(range(1, total + 1, chunk_size), 1):
        end = min(start + chunk_size - 1, total)
        chunk_pdf = stamped(step_dir / "chunks" / f"chunk_{i:03d}_p{start}-{end}.pdf")
        pdfutil.write_pages(pdf, range(start, end + 1), chunk_pdf)
        chunks.append((chunk_pdf, start, end))

    def classify(chunk):
        chunk_pdf, start, end = chunk
        n = end - start + 1
        result = get_ai().run(
            FILTER_PROMPT.format(path=chunk_pdf, n=n),
            model=report.model,
            effort=report.effort,
            schema=schemas.CLASSIFY_PAGES,
            report=report,
            add_dirs=[out_dir],
            files=[chunk_pdf],
        )
        by_page = {p["page"]: p for p in result["pages"]}
        rows = []
        for rel in range(1, n + 1):
            p = by_page.get(rel)
            rows.append(
                {
                    "page": start + rel - 1,
                    # never silently drop a page the model skipped
                    "is_borehole_log": p["is_borehole_log"] if p else True,
                    "reason": p["reason"] if p else "not classified by model, kept",
                }
            )
        return rows

    with ThreadPoolExecutor(workers) as pool:
        pages = [row for rows in pool.map(classify, chunks) for row in rows]

    kept = [p["page"] for p in pages if p["is_borehole_log"]]
    recorder.record(
        "filter",
        {"source": pdf.name, "total_pages": total, "kept_pages": kept, "pages": pages},
        report=report,
        path=stamped(step_dir / "classification.json"),
    )
    log(f"step 1: keeping {len(kept)} of {total} pages")
    if not kept:
        return None
    dest = stamped(step_dir / "borehole_pages.pdf")
    pdfutil.write_pages(pdf, kept, dest)
    hints = [p["reason"] for p in pages if p["is_borehole_log"]]
    return dest, hints
