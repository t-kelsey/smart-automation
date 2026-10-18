"""The four pipeline steps. Each writes its intermediate output below `out_dir`."""

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from .. import coordinate_systems, din4023, pdfutil, schemas
from ..naming import base, stamped
from ..output import Recorder, dump_json
from ..ai import PipelineError, StepReport, get_ai, log

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
- Coordinates: x = easting/longitude, y = northing/latitude, as plain numbers exactly as
  written. Set x and y whenever the source gives numeric coordinates, even if the coordinate
  system or datum is unclear — never drop real numbers just because the projection is
  uncertain. Always set epsg to null; it is resolved separately from source_coordinate_system
  and source_coordinate_raw, not by you. Always keep the coordinate system's name/label in
  source_coordinate_system and the raw coordinate text in source_coordinate_raw.
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

GUESS_EPSG_PROMPT = """This borehole has coordinates but no coordinate system could be matched
from an explicit label in the source. Estimate the approximate real-world location, so the point
can still be shown on a map — an approximate location beats none, as long as it's flagged as a
guess (which the caller already does).

place: {place}
client: {client}
project: {project}
source_coordinate_system (as written, possibly empty): {system}
source_coordinate_raw: {raw}
x (easting/longitude): {x}
y (northing/latitude): {y}

Rules:
- Infer the country/region/city from place/client/project (e.g. a project name often names a real
  place even with no dedicated place field).
- approx_lon/approx_lat: your best-guess decimal-degree coordinates of that place (not the EPSG
  code or UTM zone — those are computed separately from your estimate), or both null if place/
  client/project give no location clue at all.
- reasoning: one short sentence naming the clue you used (country, coordinate magnitude, etc.)."""


def _maybe_guess_epsg(borehole: dict, report: StepReport) -> str | None:
    """Best-effort, explicitly-flagged EPSG guess (haiku) when coordinate_systems.resolve() found
    nothing but x/y are present. Returns a validation-issue string if it guessed, else None."""
    if borehole.get("x") is None or borehole.get("y") is None or borehole.get("epsg") is not None:
        return None
    try:
        guess = get_ai().run(
            GUESS_EPSG_PROMPT.format(
                place=borehole.get("place"),
                client=borehole.get("client"),
                project=borehole.get("metadata", {}).get("project"),
                system=borehole.get("source_coordinate_system"),
                raw=borehole.get("source_coordinate_raw"),
                x=borehole["x"],
                y=borehole["y"],
            ),
            model=report.model,
            effort="low",
            schema=schemas.GUESS_EPSG,
            report=report,
            tools="",
            max_turns=1,
        )
    except Exception as e:
        log(f"step 4: epsg guess failed, leaving epsg null: {e}")
        return None
    lon, lat = guess.get("approx_lon"), guess.get("approx_lat")
    if lon is None or lat is None:
        return None
    epsg = coordinate_systems.utm_epsg(lon, lat)
    if epsg is None:
        return None
    borehole["epsg"] = epsg
    reasoning = guess.get("reasoning") or "no reasoning given"
    borehole.setdefault("metadata", {})["epsg_guessed_by_ai"] = reasoning
    return f"epsg {epsg} is an AI guess ({reasoning}), not from an explicit label in the source"


def transform_boreholes(
    extracted: list[tuple[pathlib.Path, dict]],
    out_dir: pathlib.Path,
    report: StepReport,
    workers: int,
    recorder: Recorder = Recorder(),
) -> list[dict]:
    step_dir = out_dir / "04_transform"
    log(f"step 4: transforming {len(extracted)} borehole(s) to the database schema")

    def transform(item: tuple[int, tuple[pathlib.Path, dict]]):
        position, (f, data) = item
        part = report.child(f"#{position}")  # this borehole's share of the step's usage
        try:
            recorder.start("transform", part, position=position)
            payload = get_ai().run(
                TRANSFORM_PROMPT.format(
                    data=json.dumps(data, ensure_ascii=False, indent=1), din4023=din4023.vocabulary_hint()
                ),
                model=report.model,
                effort=report.effort,
                schema=schemas.DB_PAYLOAD,
                report=part,
                tools="",
                max_turns=2,
            )
            payload, din_issues = din4023.conform(payload)
            coordinate_systems.resolve(payload["borehole"])
            guess_issue = _maybe_guess_epsg(payload["borehole"], part)
        except Exception as e:
            recorder.record_failure("transform", e, report=part, position=position)
            raise
        issues = validate_payload(payload) + din_issues
        if guess_issue:
            issues.append(guess_issue)
        for i in issues:
            log(f"step 4: WARNING {f.stem}: {i}")
        recorder.record(
            "transform",
            {"payload": payload, "validation_issues": issues},
            report=part,
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
        issues.append(
            f"x/y present but epsg could not be resolved from "
            f"{b.get('source_coordinate_system')!r} ({b.get('source_coordinate_raw')!r}); "
            "location will not be set"
        )
    for l in p["layers"]:
        pos = l["position"]
        if l["depth_from_m"] < 0 or l["depth_to_m"] <= l["depth_from_m"]:
            issues.append(f"layer {pos}: invalid depth range {l['depth_from_m']}..{l['depth_to_m']}")
    return issues
