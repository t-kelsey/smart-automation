"""Step 5: an independent model checks the transform payload against the page images (ADR-0006).

It returns a verdict and a pixel box per borehole field and layer. `corrected` values are applied
(and logged as edits), `uncertain`/`wrong` become warning/error flags (with the coerced
`corrected_value`, if usable, as `suggestion`), and the boxes become the
`sources` of the borehole and its layers. The step's result is what the server posts to the API.
"""

import copy
import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from .. import din4023, pdftext, pdfutil, schemas
from ..ai import StepReport, get_ai, log
from ..naming import base, stamped
from ..openrouter import RENDER_DPI
from ..output import Recorder

BOREHOLE_FIELDS = (
    "name", "external_id", "purpose", "place", "client", "drilling_method", "drilled_at", "end_date",
    "location", "total_depth_m", "borehole_length_m", "elevation_m", "groundwater_level_m",
)  # fmt: skip
LAYER_FIELDS = ("depth_from_m", "depth_to_m", "stratigraphy", "petrography", "color")
NUMBERS = {"total_depth_m", "borehole_length_m", "elevation_m", "groundwater_level_m", "depth_from_m", "depth_to_m"}
REQUIRED = {"name", "depth_from_m", "depth_to_m"}
SEVERITY = {"uncertain": "warning", "wrong": "error"}

VALIDATE_PROMPT = """You are an independent checker. Another model extracted a borehole log into the
payload below; you have not seen its reasoning. Compare it with the borehole log, given as
{n} page images ({path}), and judge every value against what the document shows.

Page image sizes in pixels (width x height): {sizes}.

Payload (JSON):
{payload}

Notes from the extraction (doubtful or illegible parts): {warnings}
Issues found by the pipeline's own checks: {issues}

Return:
- borehole_fields: one entry per borehole field that has a value in the payload OR that the
  document clearly shows although the payload has null. Fields: {borehole_fields}. "location"
  stands for the coordinates (x, y, epsg).
- layers: one entry per payload layer, matched by its position. box = the whole row/interval of the
  layer in the log. field_boxes: page and box of each layer field ({layer_fields}) where it is
  written: depth_from_m/depth_to_m around the depth number on the depth scale or in the depth
  column, petrography around the soil/rock description, stratigraphy and color around their words
  (often inside the description). Leave out fields not written anywhere. In "fields" list only the
  layer fields that are not ok.

For each: page = 1-based page in this PDF where the value is written, box = [x0, y0, x1, y1] in
PIXELS of that page image (origin top left) tightly around the written value; page/box null if it is
not visible anywhere. verdict:
- ok: the value matches the document (translation to English and unit conversion are fine).
- corrected: you are sure the value is wrong AND you know the right one; give it in corrected_value
  in the payload's format (numbers in metres, ISO dates, location as {{"x", "y", "epsg"}},
  petrography as a German DIN 4023 term: {din4023}).
- uncertain: doubtful (hard to read, ambiguous); put your best guess, if any, in corrected_value
  (same format as for corrected; it is shown to the reviewer, not applied) and explain in message.
- wrong: contradicts the document, the right value is unknown.
Give a short message for every verdict that is not ok. Do not invent values."""


def _num(v) -> float:
    if v is None or isinstance(v, bool):
        raise ValueError(f"not a number: {v!r}")
    return float(v)


def _coerce(field: str, value):
    """`value` in the payload's format; raises ValueError if it cannot be applied."""
    if value is None or value == "":
        if field in REQUIRED or field == "location":
            raise ValueError("no value")
        return None
    if field in NUMBERS:
        return _num(value)
    if field == "location":
        if not isinstance(value, dict):
            raise ValueError(f"not a location: {value!r}")
        return {"x": _num(value.get("x")), "y": _num(value.get("y")), "epsg": int(value["epsg"]) if value.get("epsg") else None}
    if field == "petrography":
        canon = din4023.normalise_petrography(str(value))
        if canon is None:
            raise ValueError(f"{value!r} is not a DIN 4023 term")
        return canon
    return str(value)


def pixel_box(raw, page: int | None, sizes: list[tuple[int, int]], words: dict[int, list], values=()) -> list[float] | None:
    """A model pixel box as [x0, y0, x1, y1] in 0-1 of the page (clamped, then snapped to `values` in
    the text layer, else tightened to its words), or None if it is unusable."""
    if page is None or not 1 <= page <= len(sizes) or not isinstance(raw, list) or len(raw) != 4:
        return None
    w, h = sizes[page - 1]
    try:
        x0, y0, x1, y1 = (min(max(float(v) / d, 0.0), 1.0) for v, d in zip(raw, (w, h, w, h)))
    except (TypeError, ValueError):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    box, page_words = [x0, y0, x1, y1], words.get(page)
    box = pdftext.snap(box, page_words, list(values)) if values else pdftext.tighten(box, page_words)
    return [round(v, 4) for v in box]


def _source(entry: dict, sizes, words, values=()) -> dict | None:
    page = entry.get("page")
    if not isinstance(page, int) or not 1 <= page <= len(sizes):
        return None
    return {"page": page, "box": pixel_box(entry.get("box"), page, sizes, words, values)}


def _written(target: dict, field: str) -> list:
    """The value(s) of `field` to look for in the text layer (location: x and y as written)."""
    values = [target.get("x"), target.get("y")] if field == "location" else [target.get(field)]
    return [v for v in values if v not in (None, "")]


def apply_verdicts(payload: dict, verdicts: dict, sizes, words) -> tuple[dict, list[dict], list[dict]]:
    """(payload with corrections and sources, flags, edits) from the validator's answer."""
    out = copy.deepcopy(payload)
    b = out["borehole"]
    layers = {l["position"]: l for l in out["layers"]}
    flags: list[dict] = []
    edits: list[dict] = []

    def judge(target: dict, check: dict, position: int | None) -> None:
        field, verdict, message = check.get("field"), check.get("verdict"), check.get("message") or ""
        suggestion = None
        if verdict in SEVERITY and check.get("corrected_value") not in (None, ""):
            try:  # a usable suggestion is shown to the reviewer, not applied
                suggestion = _coerce(field, check["corrected_value"])
            except (ValueError, TypeError, AttributeError):
                pass
        if verdict == "corrected":
            old = {k: target.get(k) for k in ("x", "y", "epsg")} if field == "location" else target.get(field)
            try:
                new = _coerce(field, check.get("corrected_value"))
            except (ValueError, TypeError, AttributeError) as e:
                verdict, message = "uncertain", f"{message} (suggested {check.get('corrected_value')!r}, not applied: {e})"
            else:
                if field == "location":
                    new["epsg"] = new["epsg"] or old["epsg"]
                    target.update(new)
                else:
                    target[field] = new
                if new != old:
                    edits.append(
                        {"field": field, "layer_position": position, "old_value": old, "new_value": new, "reason": message}
                    )
        if verdict in SEVERITY:
            flags.append(
                {"field": field, "layer_position": position, "severity": SEVERITY[verdict], "message": message,
                 "suggestion": suggestion, "origin": "validator", "code": None}
            )  # fmt: skip

    sources = {}
    for check in verdicts.get("borehole_fields") or []:
        if check.get("field") not in BOREHOLE_FIELDS:
            continue
        judge(b, check, None)
        if source := _source(check, sizes, words, _written(b, check["field"])):
            sources[check["field"]] = source
    b["sources"] = sources
    for entry in verdicts.get("layers") or []:
        layer = layers.get(entry.get("position"))
        if layer is None:
            continue
        for check in entry.get("fields") or []:
            if check.get("field") in LAYER_FIELDS:
                judge(layer, check, layer["position"])
        layer["source"] = _source(entry, sizes, words)
        layer["sources"] = {
            fb["field"]: s
            for fb in entry.get("field_boxes") or []
            if fb.get("field") in LAYER_FIELDS and (s := _source(fb, sizes, words, _written(layer, fb["field"])))
        }
    if guess := (b.get("metadata") or {}).get("epsg_guessed_by_ai"):
        note = f"EPSG {b.get('epsg')} is an AI guess: {guess}"
        # one flag per concern: if the validator already doubts the location, the guess goes into it
        if own := next((f for f in flags if f["field"] == "location" and f["layer_position"] is None), None):
            own["message"] = f"{own['message']} ({note})".strip()
        else:
            flags.append(
                {"field": "location", "layer_position": None, "severity": "warning", "origin": "rule",
                 "code": "epsg_guessed", "suggestion": None, "message": note}
            )  # fmt: skip
    return out, flags, edits


def validate_boreholes(
    items: list[tuple[pathlib.Path, dict, dict]],
    out_dir: pathlib.Path,
    report: StepReport,
    workers: int,
    recorder: Recorder = Recorder(),
    first_position: int = 1,
) -> list[dict]:
    """`items`: (split-out PDF, extract result, transform result) per borehole."""
    step_dir = out_dir / "05_validate"
    log(f"step 5: validating {len(items)} borehole(s)")

    def validate(item: tuple[int, tuple[pathlib.Path, dict, dict]]):
        position, (f, extracted, transformed) = item
        part = report.child(f"#{position}")
        try:
            recorder.start("validate", part, position=position)
            sizes = pdfutil.page_pixel_sizes(f, RENDER_DPI)
            ai = get_ai()
            # a backend that reads files itself gets the pages pre-rendered, so the pixel sizes match
            pages = [f] if ai.renders_pages else pdfutil.render_page_images(f, step_dir / f"{base(f.stem)}_pages", RENDER_DPI)
            verdicts = ai.run(
                VALIDATE_PROMPT.format(
                    path=", ".join(str(p) for p in pages),
                    n=len(sizes),
                    sizes=", ".join(f"page {i}: {w} x {h}" for i, (w, h) in enumerate(sizes, 1)),
                    payload=json.dumps(transformed["payload"], ensure_ascii=False, indent=1),
                    warnings=json.dumps((extracted or {}).get("warnings") or [], ensure_ascii=False),
                    issues=json.dumps(transformed.get("validation_issues") or [], ensure_ascii=False),
                    borehole_fields=", ".join(BOREHOLE_FIELDS),
                    layer_fields=", ".join(LAYER_FIELDS),
                    din4023=din4023.vocabulary_hint(),
                ),
                model=report.model,
                effort=report.effort,
                schema=schemas.VALIDATE,
                report=part,
                add_dirs=list({p.parent for p in pages}),
                files=pages,
                max_turns=8,
            )
            payload, flags, edits = apply_verdicts(transformed["payload"], verdicts, sizes, pdftext.words(f))
        except Exception as e:
            recorder.record_failure("validate", e, report=part, position=position)
            raise
        log(f"step 5: {f.stem}: {len(flags)} flag(s), {len(edits)} correction(s)")
        data = {"payload": payload, "flags": flags, "edits": edits, "verdicts": verdicts}
        recorder.record("validate", data, report=part, position=position, path=stamped(step_dir / f"{base(f.stem)}.json"))
        return data | {"validation_issues": transformed.get("validation_issues") or [], "source_file": f.name}

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(validate, enumerate(items, first_position)))
