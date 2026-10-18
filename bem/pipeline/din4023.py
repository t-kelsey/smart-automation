"""DIN 4023 conformity of a borehole payload, checked against standards/din-4023/din-4023.json.

A payload conforms when
- it has at least one layer, and layers are ordered by depth without overlaps,
- every layer's `petrography` is empty (not in the source) or a DIN 4023 term: a main component
  (Table 1 name, hatch name or short form, e.g. "Sand", "Sandstein", "S") optionally followed by
  secondary components (Table 1 adjectives or short forms, e.g. "schluffig", "u"), comma separated:
  "Sand, schluffig".

`conform` rewrites each petrography to the standard's spelling ("sand,schluffig" -> "Sand, schluffig")
and keeps a changed original in the layer's `metadata.petrography_original`. Terms that cannot be
mapped are reported as issues; nothing is guessed. `color` and `stratigraphy` are not defined by
the standard (Annex A colours are drawing colours per soil type) and pass through unchanged.
"""

import copy
import json
import os
import pathlib
import re
from functools import lru_cache

STANDARD_FILE = pathlib.Path(__file__).resolve().parents[2] / "standards" / "din-4023" / "din-4023.json"


class Din4023Error(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues))
        self.issues = issues


def _fold(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip().casefold().replace("/", ", "))
    t = re.sub(r"\s*,\s*", ", ", t)
    return t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


@lru_cache
def _vocabulary() -> dict:
    path = pathlib.Path(os.environ.get("DIN_4023_FILE", STANDARD_FILE))
    d = json.loads(path.read_text(encoding="utf-8"))
    soils = d["tabelle_1"]["bodenarten"]
    soil_by_hatch = {b["schraffur"]: b for b in soils if b.get("schraffur")}

    main: dict[str, str] = {}  # folded name/id -> canonical
    main_short: dict[str, str] = {}  # exact short form -> canonical
    secondary: dict[str, str] = {}
    secondary_short: dict[str, str] = {}

    for b in soils:
        canon = b["benennung"]["hauptanteil"]
        main[_fold(canon)] = main[_fold(b["id"])] = canon
        main_short[b["kurzform"]["hauptanteil"]] = canon
        if b["benennung"]["nebenanteil"]:
            names = [n.strip() for n in b["benennung"]["nebenanteil"].split(", ")]
            for n in names:
                secondary[_fold(n)] = n
            # "torfig, humos" has one short form for both words
            secondary_short[b["kurzform"]["nebenanteil"]] = ", ".join(names)
    for h in d["schraffuren"]:
        soil = soil_by_hatch.get(h["id"])
        canon = soil["benennung"]["hauptanteil"] if soil else h["bezeichnung"]
        main[_fold(h["bezeichnung"])] = main[_fold(h["id"])] = canon
        if h.get("kurzform"):
            main_short.setdefault(h["kurzform"], canon)
    return {
        "main": main,
        "main_short": main_short,
        "secondary": secondary,
        "secondary_short": secondary_short,
        "canonical": sorted(set(main.values())),
        "adjectives": sorted(set(secondary.values())),
    }


def vocabulary_hint() -> str:
    """The allowed terms as prompt text."""
    v = _vocabulary()
    return (
        "Main component (exactly one): " + ", ".join(v["canonical"]) + ". "
        "Optional secondary components after it, comma separated: " + ", ".join(v["adjectives"]) + "."
    )


def normalise_petrography(text: str | None) -> str | None:
    """The DIN 4023 spelling of `text`, or None if it is not a DIN 4023 term."""
    if not text or not text.strip():
        return None
    v = _vocabulary()
    tokens = [t.strip() for t in re.split(r"\s*[,;]\s*|\s+und\s+", text.strip()) if t.strip()]
    main = rest = None
    for n in (2, 1):  # "Torf, Humus" is one name containing a comma
        if len(tokens) >= n:
            cand = ", ".join(tokens[:n])
            canon = v["main"].get(_fold(cand)) or (v["main_short"].get(cand) if n == 1 else None)
            if canon:
                main, rest = canon, tokens[n:]
                break
    if main is None:
        return None
    secs: list[str] = []
    for t in rest:
        canon = v["secondary"].get(_fold(t)) or v["secondary_short"].get(t)
        if canon is None:
            return None
        secs += [s for s in canon.split(", ") if s not in secs]
    return ", ".join([main, *secs])


def conform(payload: dict) -> tuple[dict, list[str]]:
    """Return (payload with DIN 4023 petrography, issues). Issues must be empty to upload."""
    out = copy.deepcopy(payload)
    issues: list[str] = []
    layers = out.get("layers") or []
    if not layers:
        issues.append("no layers")
    prev_to = None
    for i, layer in enumerate(layers, 1):
        pos = layer.get("position", i)
        original = layer.get("petrography")
        if original and original.strip():
            canon = normalise_petrography(original)
            if canon is None:
                issues.append(f"layer {pos}: petrography {original!r} is not a DIN 4023 term")
            else:
                if canon != original:
                    layer.setdefault("metadata", {})["petrography_original"] = str(original)
                layer["petrography"] = canon
        else:
            layer["petrography"] = None
        f, t = layer.get("depth_from_m"), layer.get("depth_to_m")
        if f is None or t is None or not t > f:
            issues.append(f"layer {pos}: invalid depth range {f}..{t}")
        elif prev_to is not None and f < prev_to:
            issues.append(f"layer {pos}: starts at {f} m, above the end of the previous layer ({prev_to} m)")
        if t is not None:
            prev_to = t
    return out, issues
