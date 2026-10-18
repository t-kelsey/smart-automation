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


def extract_boreholes(
    files: list[pathlib.Path],
    out_dir: pathlib.Path,
    report: StepReport,
    workers: int,
    recorder: Recorder = Recorder(),
    first_position: int = 1,
) -> list[tuple[pathlib.Path, dict]]:
    step_dir = out_dir / "03_extract"
    log(f"step 3: extracting {len(files)} borehole(s)")

    def extract(item: tuple[int, pathlib.Path]):
        position, f = item
        part = report.child(f"#{position}")  # this borehole's share of the step's usage
        try:
            recorder.start("extract", part, position=position)
            n = pdfutil.page_count(f)
            data = get_ai().run(
                EXTRACT_PROMPT.format(path=f, n=n, max_pages=MAX_READ_PAGES),
                model=report.model,
                effort=report.effort,
                schema=schemas.EXTRACT_BOREHOLE,
                report=part,
                add_dirs=[out_dir],
                files=[f],
                max_turns=8 + n // MAX_READ_PAGES * 2,
            )
        except Exception as e:
            recorder.record_failure("extract", e, report=part, position=position)
            raise
        recorder.record("extract", data, report=part, position=position, path=stamped(step_dir / f"{base(f.stem)}.json"))
        if not data["is_single_borehole"]:
            log(f"step 3: WARNING {f.name} holds {data['borehole_count_in_file']} boreholes")
        return f, data

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(extract, enumerate(files, first_position)))
