"""The four pipeline steps. Each writes its intermediate output below `out_dir`."""

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from .. import din4023, pdfutil, schemas
from ..naming import base, stamped
from ..output import Recorder, dump_json
from ..ai import AI, PipelineError, StepReport, get_ai, log

MAX_READ_PAGES = 20  # the Read tool renders at most 20 PDF pages per call


def _dump(path: pathlib.Path, data) -> None:
    dump_json(stamped(path), data)


# --------------------------------------------------------------------------
# Step 4: format/translate to the database schema       (haiku, high effort)
# --------------------------------------------------------------------------

TRANSFORM_PROMPT = """Convert this borehole extraction into the payload for our database
API (POST /api/boreholes). Input JSON:

{data}

Rules:
- Translate all free text to English, but keep proper nouns (place, client, person and
  project names) unchanged.
- borehole.name: the borehole designation (e.g. "B 1/59"), never null; fall back to
  the project or place name only if no designation exists.
- Dates: ISO YYYY-MM-DD, null if not fully determinable. Do not invent day or month.
- Coordinates: set x, y and epsg only if all three are known (x = easting/longitude,
  y = northing/latitude, epsg = integer code for the stated coordinate system, e.g.
  31467 for Gauss-Krueger zone 3). Otherwise set all three to null. Always keep the
  original text in source_coordinate_raw and the system name in source_coordinate_system.
- Depths and elevation in metres, plain numbers. Depths are measured from the surface,
  >= 0, and each layer's depth_to_m must be greater than depth_from_m.
- layers: keep order, position starts at 1.
  - stratigraphy: formation/age as a short English term or the formation abbreviation
    plus its name if known; null if absent.
  - petrography: the main soil or rock type as a German DIN 4023 term, written exactly as in the
    allowed list below (this field is NOT translated to English). {din4023}
    Examples: "Sand", "Sand, schluffig", "Ton, schluffig, sandig", "Sandstein". Choose the closest
    term; never invent one.
  - color: English colour words only (e.g. "grey-brown"), null if absent.
  - raw_text: the original layer description exactly as extracted (untranslated).
  - metadata: remaining layer details as string key/value pairs (e.g. notes), else {{}}.
- borehole.metadata: string key/value pairs for useful header data the columns have no
  place for (project, source_language, date notes, other_information entries, warnings).
  Leave out is_single_borehole and borehole_count_in_file; they are bookkeeping.
- Do not add facts that are not in the input."""


def transform_boreholes(
    extracted: list[tuple[pathlib.Path, dict]],
    out_dir: pathlib.Path,
    report: StepReport,
    workers: int,
    recorder: Recorder = Recorder(),
    ai: AI | None = None,
) -> list[dict]:
    ai = ai or get_ai()
    step_dir = out_dir / "04_transform"
    log(f"step 4: transforming {len(extracted)} borehole(s) to the database schema")

    def transform(item: tuple[int, tuple[pathlib.Path, dict]]):
        position, (f, data) = item
        payload = ai.run(
            TRANSFORM_PROMPT.format(
                data=json.dumps(data, ensure_ascii=False, indent=1), din4023=din4023.vocabulary_hint()
            ),
            model=report.model,
            effort=report.effort,
            schema=schemas.DB_PAYLOAD,
            report=report,
            tools="",
            max_turns=2,
        )
        payload, din_issues = din4023.conform(payload)
        issues = validate_payload(payload) + din_issues
        for i in issues:
            log(f"step 4: WARNING {f.stem}: {i}")
        recorder.record(
            "transform",
            {"payload": payload, "validation_issues": issues},
            position=position,
            path=stamped(step_dir / f"{base(f.stem)}.json"),
        )
        return {"payload": payload, "validation_issues": issues, "source_file": f.name}

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(transform, enumerate(extracted, 1)))


def validate_payload(p: dict) -> list[str]:
    """Mirror the API's changeset rules locally so problems show before posting."""
    issues = []
    b = p["borehole"]
    if not (b.get("name") or "").strip():
        issues.append("borehole.name is empty (API requires it)")
    for k in ("total_depth_m", "borehole_length_m", "elevation_m", "groundwater_level_m"):
        if b.get(k) is not None and b[k] < 0:
            issues.append(f"borehole.{k} is negative (API requires >= 0)")
    xyz = [b.get("x"), b.get("y"), b.get("epsg")]
    if any(v is None for v in xyz) and not all(v is None for v in xyz):
        issues.append("x, y, epsg must be all set or all null")
    for l in p["layers"]:
        pos = l["position"]
        if l["depth_from_m"] < 0 or l["depth_to_m"] <= l["depth_from_m"]:
            issues.append(f"layer {pos}: invalid depth range {l['depth_from_m']}..{l['depth_to_m']}")
    return issues
