"""The four pipeline steps. Each writes its intermediate output below `out_dir`."""

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from .. import pdfutil, schemas
from ..naming import base, stamped
from ..output import Recorder, dump_json
from ..ai import AI, PipelineError, StepReport, get_ai, log

MAX_READ_PAGES = 20  # the Read tool renders at most 20 PDF pages per call


def _dump(path: pathlib.Path, data) -> None:
    dump_json(stamped(path), data)


# --------------------------------------------------------------------------
# Step 3: extract everything from one borehole          (sonnet, high effort)
# --------------------------------------------------------------------------

EXTRACT_PROMPT = """Read the borehole log PDF at {path} ({n} pages; the Read tool shows at
most {max_pages} pages per call). It should contain exactly ONE borehole.

First check that: set is_single_borehole and borehole_count_in_file accordingly. If it
holds several boreholes, extract only the first one and say so in warnings.

Then extract all data: header data, coordinates (exactly as written, plus parsed
numbers if unambiguous), elevation, depths, groundwater, and EVERY layer with its depth
interval. Layers carry meaning in colour and hatch pattern too: use them for
petrography/colour where the text doesn't say. Keep all text in the document's original
language and wording; do not translate here. Use null for anything not in the document,
never guess. Put anything that fits no field into other_information, and list
illegible or doubtful parts in warnings."""

EXTRACT_PROMPT_LOCAL = EXTRACT_PROMPT.replace(
    "Read the borehole log PDF at {path} ({n} pages; the Read tool shows at\nmost {max_pages} pages per call).",
    "The {n} attached images are the pages of one borehole log PDF, in order.",
)
assert "Read" not in EXTRACT_PROMPT_LOCAL


def extract_boreholes(
    files: list[pathlib.Path],
    out_dir: pathlib.Path,
    report: StepReport,
    workers: int,
    recorder: Recorder = Recorder(),
    ai: AI | None = None,
) -> list[tuple[pathlib.Path, dict]]:
    ai = ai or get_ai()
    step_dir = out_dir / "03_extract"
    log(f"step 3: extracting {len(files)} borehole(s)")

    def extract(item: tuple[int, pathlib.Path]):
        position, f = item
        total = pdfutil.page_count(f)
        # a backend with a small context sees only the first pages (flagged in the warnings below)
        n = min(total, ai.max_input_pages or total)
        prompt = EXTRACT_PROMPT if ai.reads_files else EXTRACT_PROMPT_LOCAL
        data = ai.run(
            prompt.format(path=f, n=n, max_pages=MAX_READ_PAGES),
            model=report.model,
            effort=report.effort,
            schema=schemas.EXTRACT_BOREHOLE,
            report=report,
            add_dirs=[out_dir],
            max_turns=8 + n // MAX_READ_PAGES * 2,
            inputs=[(f, f"1-{n}")],
        )
        if n < total:
            data.setdefault("warnings", []).append(f"only the first {n} of {total} pages were read (local backend page limit)")
        recorder.record("extract", data, position=position, path=stamped(step_dir / f"{base(f.stem)}.json"))
        if not data["is_single_borehole"]:
            log(f"step 3: WARNING {f.name} holds {data['borehole_count_in_file']} boreholes")
        return f, data

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(extract, enumerate(files, 1)))
