"""DIN 4023 conformity of a borehole payload, checked against standards/din-4023/din-4023.json.

A layer's `petrography` is empty (not in the source) or a DIN 4023 term: a main component
  (Table 1 name, hatch name or short form, e.g. "Sand", "Sandstein", "S") optionally followed by
  secondary components (Table 1 adjectives or short forms, e.g. "schluffig", "u"), comma separated:
  "Sand, schluffig".

`conform` rewrites each petrography to the standard's spelling ("sand,schluffig" -> "Sand, schluffig")
and keeps a changed original in the layer's `metadata.petrography_original`. Terms that cannot be
mapped become null (the API flags them as `missing_petrography`); nothing is guessed. `color` and `stratigraphy` are not defined by
the standard (Annex A colours are drawing colours per soil type) and pass through unchanged.
"""

import copy
import json
import os
import pathlib
import re
from functools import lru_cache

STANDARD_FILE = pathlib.Path(__file__).resolve().parents[2] / "standards" / "din-4023" / "din-4023.json"


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
    """Return (payload with DIN 4023 petrography, notes). Never blocks the upload (ADR-0006): a term that
    cannot be mapped becomes null with the original kept in `metadata.petrography_original` and a note;
    layer order and overlaps are checked by the API."""
    out = copy.deepcopy(payload)
    notes: list[str] = []
    for i, layer in enumerate(out.get("layers") or [], 1):
        original = layer.get("petrography")
        canon = normalise_petrography(original)
        if original and original.strip() and canon != original:
            layer.setdefault("metadata", {})["petrography_original"] = str(original)
            if canon is None:
                notes.append(f"layer {layer.get('position', i)}: petrography {original!r} is not a DIN 4023 term, set to null")
        layer["petrography"] = canon
    return out, notes
