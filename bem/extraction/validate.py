"""Step 2: checks on an extracted Bohrung.

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

from .schema import Bohrung

TOL = 1e-6

# Extend these from your own corpus. Unknown values only produce a warning.
KNOWN_BOHRART = {"Bohrung mit Ausbau", "Unbekannt"}
KNOWN_BOHRZWECK = {"Unbekannt"}

NA_STRINGS = {"keine angabe", "unbekannt"}


@dataclass
class Issue:
    level: str  # "error" | "warning"
    field: str
    message: str


def check_consistency(b: Bohrung) -> list[Issue]:
    issues: list[Issue] = []
    add = lambda level, field, msg: issues.append(Issue(level, field, msg))

    if not b.aufschlussname.strip():
        add("error", "aufschlussname", "empty")

    # --- layers -----------------------------------------------------------
    s = b.schichten
    if not s:
        add("error", "schichten", "no layers extracted")
    for i, l in enumerate(s, 1):
        if l.von_m < 0 or l.bis_m <= l.von_m:
            add("error", f"schichten[{i}]", f"invalid interval {l.von_m} - {l.bis_m}")
    for i, (a, c) in enumerate(zip(s, s[1:]), 1):
        if abs(c.von_m - a.bis_m) > TOL:
            kind = "gap" if c.von_m > a.bis_m else "overlap"
            add("error", f"schichten[{i}->{i + 1}]", f"{kind}: bis={a.bis_m} but next von={c.von_m}")
    if s and abs(s[0].von_m) > TOL:
        add("warning", "schichten[1]", f"first layer starts at {s[0].von_m} m, not 0")

    # --- depth vs Endteufe (last bis may be smaller than Endteufe, never larger) ----
    if b.endteufe_m is None:
        add("warning", "endteufe_m", "missing")
    elif s and s[-1].bis_m > b.endteufe_m + TOL:
        add("error", "endteufe_m", f"last layer ends at {s[-1].bis_m} m, below Endteufe {b.endteufe_m} m")

    # --- plausibility ---------------------------------------------------------
    k = b.koordinaten
    if k.ost is not None and not (166_000 <= k.ost <= 834_000):
        add("warning", "koordinaten.ost", f"{k.ost} outside UTM easting range")
    if k.nord is not None and not (5_200_000 <= k.nord <= 6_100_000):
        add("warning", "koordinaten.nord", f"{k.nord} outside range for Germany")
    if (k.ost is None) != (k.nord is None):
        add("warning", "koordinaten", "only one of ost/nord present")
    if b.ansatzhoehe_m is not None and not (-10 <= b.ansatzhoehe_m <= 3000):
        add("warning", "ansatzhoehe_m", f"{b.ansatzhoehe_m} implausible")
    if b.bohrdatum is not None and not (date(1800, 1, 1) <= b.bohrdatum <= date.today()):
        add("warning", "bohrdatum", f"{b.bohrdatum} implausible")

    # --- closed vocabularies -------------------------------------------------
    if b.bohrart not in KNOWN_BOHRART:
        add("warning", "bohrart", f"unknown value '{b.bohrart}'")
    if b.bohrzweck not in KNOWN_BOHRZWECK:
        add("warning", "bohrzweck", f"unknown value '{b.bohrzweck}'")
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


def check_grounding(b: Bohrung, source_text: str) -> list[Issue]:
    issues: list[Issue] = []
    text_n = _norm(source_text)

    def need_text(field: str, value: str) -> None:
        if _norm(value) in NA_STRINGS:
            return
        if _norm(value) not in text_n:
            issues.append(Issue("warning", field, f"'{value}' not found verbatim in OCR text"))

    def need_number(field: str, x: float | None) -> None:
        if x is not None and not _number_in_text(x, source_text):
            issues.append(Issue("warning", field, f"{x} not found in OCR text"))

    need_text("aufschlussname", b.aufschlussname)
    need_number("endteufe_m", b.endteufe_m)
    need_number("ansatzhoehe_m", b.ansatzhoehe_m)
    need_number("koordinaten.ost", b.koordinaten.ost)
    need_number("koordinaten.nord", b.koordinaten.nord)
    for i, l in enumerate(b.schichten, 1):
        need_number(f"schichten[{i}].von_m", l.von_m)
        need_number(f"schichten[{i}].bis_m", l.bis_m)
        need_text(f"schichten[{i}].stratigraphie", l.stratigraphie)
        need_text(f"schichten[{i}].petrographie", l.petrographie)
    return issues


def check_all(b: Bohrung, source_text: str) -> list[Issue]:
    return check_consistency(b) + check_grounding(b, source_text)


def status(issues: list[Issue]) -> str:
    if any(i.level == "error" for i in issues):
        return "error"
    return "warning" if issues else "ok"
