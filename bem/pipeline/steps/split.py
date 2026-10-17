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
# Step 2: one file per borehole                         (haiku, medium effort)
# --------------------------------------------------------------------------

SPLIT_PROMPT = """Read the PDF at {path} ({n} pages). It contains borehole log sheets
only. Work out which pages belong to which borehole and group them: every borehole gets
one entry with its page numbers (1..{n}, ascending). Continuation sheets belong to the
borehole they continue. Every page must be assigned to exactly one borehole.

{read_hint}
Use the borehole name/id written on the sheet as the label.

A previous pass noted this about each page (it may be wrong, check the pages):
{page_hints}

Give your final answer only through the structured output, not as prose."""


def split_boreholes(
    pages_pdf: pathlib.Path,
    out_dir: pathlib.Path,
    report: StepReport,
    page_hints: list[str],
    recorder: Recorder = Recorder(),
) -> list[pathlib.Path]:
    step_dir = out_dir / "02_split"
    n = pdfutil.page_count(pages_pdf)
    hint = (
        f"The Read tool shows at most {MAX_READ_PAGES} pages per call, so read in ranges "
        f'such as "1-{MAX_READ_PAGES}", "{MAX_READ_PAGES + 1}-{2 * MAX_READ_PAGES}", ...'
        if n > MAX_READ_PAGES
        else f'Read all pages with pages "1-{n}".'
    )
    prompt = SPLIT_PROMPT.format(
        path=pages_pdf,
        n=n,
        read_hint=hint,
        page_hints="\n".join(f"- page {i}: {h}" for i, h in enumerate(page_hints, 1)),
    )
    log(f"step 2: grouping {n} pages into boreholes")

    for attempt in (1, 2):
        result = get_ai().run(
            prompt,
            model=report.model,
            effort=report.effort,
            schema=schemas.SPLIT_BOREHOLES,
            report=report,
            add_dirs=[out_dir],
            max_turns=6 + n // MAX_READ_PAGES * 2,
        )
        _dump(step_dir / f"raw_response_attempt{attempt}.json", result)  # for debugging bad groupings

        # validate: pages in range, none used twice, none forgotten
        seen: set[int] = set()
        groups = []
        for g in result["boreholes"]:
            pages = sorted({p for p in g["pages"] if 1 <= p <= n} - seen)
            seen |= set(pages)
            if pages:
                groups.append({"label": g["label"], "pages": pages})
        missing = sorted(set(range(1, n + 1)) - seen)
        if groups and not missing:
            break
        log(f"step 2: attempt {attempt}/2 unusable: {len(groups)} group(s), unassigned pages {missing}")
    else:
        raise PipelineError(
            f"step 2 could not group the pages into boreholes; see raw_response_attempt*.json in {step_dir}"
        )

    files = []
    for i, g in enumerate(groups, 1):
        dest = stamped(step_dir / f"borehole_{i:02d}.pdf")
        pdfutil.write_pages(pages_pdf, g["pages"], dest)
        g["file"] = dest.name
        files.append(dest)
    recorder.record("split", {"boreholes": groups}, path=stamped(step_dir / "grouping.json"))
    log(f"step 2: {len(files)} borehole file(s): " + "; ".join(f"{g['label']} = pages {g['pages']}" for g in groups))
    return files

