"""Step 2: checks on an extracted Borehole.

Two kinds of checks:
  * consistency  - does the record make sense on its own (depth chain, ranges, enums)?
  * grounding    - do the extracted values actually appear in the OCR text?
                   This catches hallucinated numbers and names.

"error"   -> record goes to manual review
"warning" -> record is kept, but listed in review.csv
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .schema import Borehole

TOL = 1e-6

# Extend these from your own corpus. Unknown values only produce a warning.
# Empty means: no closed vocabulary yet, so nothing is checked.
KNOWN_DRILLING_METHODS: set[str] = set()
KNOWN_PURPOSES: set[str] = set()


@dataclass
class Issue:
    level: str  # "error" | "warning"
    field: str
    message: str


def check_consistency(b: Borehole) -> list[Issue]:
    issues: list[Issue] = []
    add = lambda level, field, msg: issues.append(Issue(level, field, msg))

    if not b.name.strip():
        add("error", "name", "empty")

    # --- layers -----------------------------------------------------------
    s = b.layers
    if not s:
        add("error", "layers", "no layers extracted")
    for i, l in enumerate(s, 1):
        if l.depth_from_m < 0 or l.depth_to_m <= l.depth_from_m:
            add("error", f"layers[{i}]", f"invalid interval {l.depth_from_m} - {l.depth_to_m}")
    for i, (a, c) in enumerate(zip(s, s[1:]), 1):
        if abs(c.depth_from_m - a.depth_to_m) > TOL:
            kind = "gap" if c.depth_from_m > a.depth_to_m else "overlap"
            add("error", f"layers[{i}->{i + 1}]", f"{kind}: depth_to={a.depth_to_m} but next depth_from={c.depth_from_m}")
    if s and abs(s[0].depth_from_m) > TOL:
        add("warning", "layers[1]", f"first layer starts at {s[0].depth_from_m} m, not 0")

    # --- depth vs total depth (last layer may end above it, never below) ----
    if b.total_depth_m is None:
        add("warning", "total_depth_m", "missing")
    elif s and s[-1].depth_to_m > b.total_depth_m + TOL:
        add("error", "total_depth_m", f"last layer ends at {s[-1].depth_to_m} m, below total depth {b.total_depth_m} m")

    # --- backend constraints (Api.Boreholes.Borehole changeset: these must be >= 0) -------
    for field in ("total_depth_m", "borehole_length_m", "elevation_m", "groundwater_level_m"):
        value = getattr(b, field)
        if value is not None and value < 0:
            add("error", field, f"{value} is negative; the API rejects it")

    # --- plausibility ---------------------------------------------------------
    if b.elevation_m is not None and b.elevation_m > 9000:
        add("warning", "elevation_m", f"{b.elevation_m} implausible")
    if b.drilled_at is not None and not (date(1800, 1, 1) <= b.drilled_at <= date.today()):
        add("warning", "drilled_at", f"{b.drilled_at} implausible")
    if b.drilled_at and b.end_date and b.end_date < b.drilled_at:
        add("error", "end_date", f"{b.end_date} is before drilled_at {b.drilled_at}")
    if (b.source_coordinate_raw is None) != (b.source_coordinate_system is None):
        add("warning", "source_coordinate_system", "coordinate and coordinate system should come together")

    # --- closed vocabularies (only when a list is defined) ---------------------
    if KNOWN_DRILLING_METHODS and b.drilling_method and b.drilling_method not in KNOWN_DRILLING_METHODS:
        add("warning", "drilling_method", f"unknown value '{b.drilling_method}'")
    if KNOWN_PURPOSES and b.purpose and b.purpose not in KNOWN_PURPOSES:
        add("warning", "purpose", f"unknown value '{b.purpose}'")
    return issues


# --------------------------------------------------------------------------- grounding
def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).casefold().strip()


def _number_in_text(x: float, text: str) -> bool:
    variants = set()
    for s in (f"{x:.1f}", f"{x:.2f}", f"{x:g}", repr(x)):
        variants.add(s)
        variants.add(s.replace(".", ","))
    for v in variants:
        if re.search(rf"(?<![\d.,]){re.escape(v)}(?!\d)", text):
            return True
    return False


def check_grounding(b: Borehole, source_text: str) -> list[Issue]:
    issues: list[Issue] = []
    text_n = _norm(source_text)

    def need_text(field: str, value: str | None) -> None:
        if not value:
            return
        if _norm(value) not in text_n:
            issues.append(Issue("warning", field, f"'{value}' not found verbatim in OCR text"))

    def need_number(field: str, x: float | None) -> None:
        if x is not None and not _number_in_text(x, source_text):
            issues.append(Issue("warning", field, f"{x} not found in OCR text"))

    need_text("name", b.name)
    need_text("external_id", b.external_id)
    need_text("source_coordinate_raw", b.source_coordinate_raw)
    need_number("total_depth_m", b.total_depth_m)
    need_number("borehole_length_m", b.borehole_length_m)
    need_number("elevation_m", b.elevation_m)
    need_number("groundwater_level_m", b.groundwater_level_m)
    for i, l in enumerate(b.layers, 1):
        need_number(f"layers[{i}].depth_from_m", l.depth_from_m)
        need_number(f"layers[{i}].depth_to_m", l.depth_to_m)
        need_text(f"layers[{i}].stratigraphy", l.stratigraphy)
        need_text(f"layers[{i}].petrography", l.petrography)
        need_text(f"layers[{i}].color", l.color)
        need_text(f"layers[{i}].raw_text", l.raw_text)
    return issues


def check_all(b: Borehole, source_text: str) -> list[Issue]:
    return check_consistency(b) + check_grounding(b, source_text)


def status(issues: list[Issue]) -> str:
    if any(i.level == "error" for i in issues):
        return "error"
    return "warning" if issues else "ok"
