"""Deterministic EPSG lookup for the free-text coordinate system labels borehole logs use.

The transform step (`steps/translate.py`) asks a small, fast model to extract the as-written
easting/northing numbers and the coordinate system's name, but does **not** ask it to pick an
EPSG code: a wrong-but-confident guess silently plots a borehole in the wrong place, which is
worse than leaving `epsg` (and therefore the map location) empty. `resolve()` fills `epsg`
afterwards, deterministically, from `source_coordinate_system`/`source_coordinate_raw` — never
guessing, like `din4023.normalise_petrography`.

Two kinds of matches:

1. Named systems (`_NAMED_SYSTEMS`): a fixed table of (pattern, epsg) pairs for systems that
   aren't a formula, researched from the EPSG registry (https://epsg.org) for the regions this
   project sees borehole logs from (DACH, France, Spain, the UK/Ireland, the Benelux and Nordics,
   Switzerland/Austria, Malaysia/Singapore, Australia). Ordered most-specific-first since e.g.
   "Lambert 93" must be tried before a bare "Lambert".
2. Generic UTM-family projections (`_UTM_DATUM_BASE`): these *are* a formula (EPSG code =
   a per-datum base plus the zone number, split by hemisphere for true UTM), so any zone/datum
   combination resolves without needing to enumerate every zone by hand.

This table is necessarily incomplete — extend it as new coordinate system labels show up in
`validation_issues` (logged as "coordinate system ... not recognised") rather than guessing.
"""

import re
import unicodedata
from dataclasses import dataclass


def _fold(text: str) -> str:
    """Casefold and transliterate German umlauts/ß (ü -> ue, ß -> ss, like din4023._fold), then
    strip any other accents (e.g. French/Spanish) so patterns can stay plain ASCII."""
    t = text.casefold()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t).strip()


@dataclass(frozen=True)
class _Named:
    pattern: re.Pattern
    epsg: int
    label: str


def _n(regex: str, epsg: int, label: str) -> _Named:
    return _Named(re.compile(regex), epsg, label)


# Ordered most-specific first. Patterns run against `_fold(text)`, so write them lower-case,
# unaccented, with "-" matched as `[-\s]?` where a document might render it as a space instead.
_NAMED_SYSTEMS: list[_Named] = [
    # --- Global / generic ---------------------------------------------------------------
    _n(r"\bwgs[-\s]?84\b.{0,30}\b(lat|long|longitude|latitude|geographic)\b", 4326, "WGS 84 (lat/long)"),
    # --- Austria ----------------------------------------------------------------------------
    _n(r"\bmgi\b.{0,30}\bm28\b|\baustria\b.{0,15}\bgk\b.{0,15}\bm28\b", 31254, "MGI / Austria GK M28"),
    _n(r"\bmgi\b.{0,30}\bm31\b|\baustria\b.{0,15}\bgk\b.{0,15}\bm31\b", 31255, "MGI / Austria GK M31"),
    _n(r"\bmgi\b.{0,30}\bm34\b|\baustria\b.{0,15}\bgk\b.{0,15}\bm34\b", 31256, "MGI / Austria GK M34"),
    # --- Switzerland --------------------------------------------------------------------
    _n(r"ch1903\+|lv95", 2056, "CH1903+ / LV95"),
    _n(r"ch1903(?!\+)|lv03", 21781, "CH1903 / LV03"),
    # --- France -----------------------------------------------------------------------------
    _n(r"lambert[-\s]?93", 2154, "RGF93 / Lambert-93"),
    _n(r"lambert[-\s]?(?:ii|2)[-\s]?(?:e|etendu|extended)", 27572, "NTF / Lambert II etendu"),
    _n(r"lambert[-\s]?(?:i|1)\b", 27571, "NTF / Lambert I"),
    _n(r"lambert[-\s]?(?:ii|2)\b", 27572, "NTF / Lambert II"),
    _n(r"lambert[-\s]?(?:iii|3)\b", 27573, "NTF / Lambert III"),
    _n(r"lambert[-\s]?(?:iv|4)\b", 27574, "NTF / Lambert IV"),
    # --- Benelux ------------------------------------------------------------------------
    _n(r"amersfoort|rd[-\s]?new|rijksdriehoek", 28992, "Amersfoort / RD New"),
    _n(r"lambert[-\s]?2008", 3812, "ETRS89 / Belgian Lambert 2008"),
    _n(r"lambert[-\s]?72", 31370, "BD72 / Belgian Lambert 72"),
    # --- United Kingdom / Ireland ---------------------------------------------------------
    _n(r"osgb[-\s]?(?:36)?|british national grid", 27700, "OSGB36 / British National Grid"),
    _n(r"\bitm\b|irish transverse mercator", 2157, "IRENET95 / Irish Transverse Mercator"),
    _n(r"irish grid|tm65", 29903, "TM65 / Irish Grid"),
    # --- Spain / Portugal -----------------------------------------------------------------
    _n(r"portugal[-\s]?tm0?6|etrs89.{0,15}portugal", 3763, "ETRS89 / Portugal TM06"),
    # --- Nordics ----------------------------------------------------------------------------
    _n(r"sweref[-\s]?99[-\s]?tm", 3006, "SWEREF99 TM"),
    _n(r"etrs[-\s]?tm35fin|tm35fin", 3067, "ETRS89 / TM35FIN (Finland)"),
    # --- Malaysia / Singapore ---------------------------------------------------------------
    _n(r"gdm[-\s]?2000.{0,20}rso|rso.{0,20}gdm[-\s]?2000", 3375, "GDM2000 / Peninsula RSO (Malaysia)"),
    _n(r"kertau.{0,20}rso|rso.{0,20}malaya", 29873, "Kertau / RSO Malaya (m) (Malaysia, pre-GDM2000)"),
    _n(r"\bsvy21\b", 3414, "SVY21 (Singapore)"),
    # Australia's GDA94/GDA2020 "MGA" zones are not true UTM (the datum itself covers the whole,
    # southern-hemisphere-only country, there's no N/S suffix) — handled by `_resolve_mga` instead.
]

# DHDN / Gauss-Kruger zone 2-5 (pre-ETRS89 German surveying; zone == Streifen number). A formula
# like the UTM one below: EPSG = 31464 + zone. Matches both the folded umlaut ("kruger") and the
# ASCII transliteration some documents use instead ("krueger").
_DHDN_GK = re.compile(r"gauss[-\s]?kr[u]?e?ger.{0,25}\b([2-5])\b|\b([2-5])\b.{0,25}gauss[-\s]?kr[u]?e?ger")

# Pure-UTM datum families: EPSG code = base + zone (1-60), base depends on hemisphere where the
# datum has one. `None` means that hemisphere isn't published for this datum (not used in practice
# for borehole surveying, e.g. ED50 south).
_UTM_DATUM_BASE: dict[str, dict[str, int | None]] = {
    "wgs84": {"N": 32600, "S": 32700},
    "etrs89": {"N": 25800, "S": None},
    "ed50": {"N": 23000, "S": None},
    "nad83": {"N": 26900, "S": None},
    "nad27": {"N": 26700, "S": None},
}

_DATUM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"etrs[-\s]?89"), "etrs89"),
    (re.compile(r"\bed[-\s]?50\b"), "ed50"),
    (re.compile(r"nad[-\s]?83"), "nad83"),
    (re.compile(r"nad[-\s]?27"), "nad27"),
    (re.compile(r"wgs[-\s]?84"), "wgs84"),
]

# MGRS latitude band letters: C-M south of the equator, N-X north (I and O are skipped).
_SOUTH_BANDS = set("CDEFGHJKLM")

# A tight zone+letter token like "32U" or "48N" (no space) is distinctive enough on its own
# (as on the LGRB borehole map) to imply UTM without needing a literal "UTM" keyword nearby.
_COMPACT_ZONE_LETTER = re.compile(r"\b(\d{1,2})([c-hj-np-x])\b")
# Looser form that does need a keyword nearby: "UTM zone 32 N", "UTM Sone 32", "UTM zona 31".
_UTM_ZONE_HEMI = re.compile(r"\b(\d{1,2})\s+([ns]|[c-hj-np-x])\b")
# The zone number anchored on the zone keyword itself (not just "utm" generically) — "utm" alone
# is too loose and can grab an unrelated nearby number, e.g. the "84" in "UTM WGS 84, Zone 32".
# Keyword-then-number only ("Zone 32", "Sone 32"): the reverse order is both rare in practice and
# too easily confused with an unrelated number shortly before the keyword (same "WGS 84" example).
_UTM_ZONE_NEAR_KEYWORD = re.compile(r"\b(?:zone|sone|huso|zona)\b\D{0,4}(\d{1,2})\b")
# Bare "UTM 32" (no "zone" word): only a tight gap counts, so a datum name in between ("UTM WGS 84")
# can't be mistaken for this — "wgs "/"etrs89 " etc. are all longer than 3 characters.
_UTM_TIGHT_NEAR = re.compile(r"\butm\b\D{0,3}(\d{1,2})\b")
_UTM_KEYWORD = re.compile(r"\butm\b|\bsone\b|\bhuso\b|\bzona\b|\bzone\b")


def _hemisphere(letter: str) -> str:
    """N/S are ambiguous (also valid MGRS band letters, both in the northern hemisphere), but
    geotechnical reports almost always mean them as a literal hemisphere suffix, not an MGRS grid
    reference, so those two letters are special-cased; any other letter is a true band letter."""
    letter = letter.upper()
    if letter in ("N", "S"):
        return letter
    return "S" if letter in _SOUTH_BANDS else "N"


def _resolve_utm(text: str) -> int | None:
    datum = "wgs84"  # the overwhelming default when a datum isn't named
    for pattern, name in _DATUM_PATTERNS:
        if pattern.search(text):
            datum = name
            break
    m = _COMPACT_ZONE_LETTER.search(text)
    if m is None and _UTM_KEYWORD.search(text):
        m = _UTM_ZONE_HEMI.search(text)
    if m is not None:
        zone, hemi = int(m.group(1)), _hemisphere(m.group(2))
    elif _UTM_KEYWORD.search(text):
        m = _UTM_ZONE_NEAR_KEYWORD.search(text) or _UTM_TIGHT_NEAR.search(text)
        if not m:
            return None
        zone, hemi = int(m.group(1)), "N"  # no hemisphere given: assume north (far more common)
    else:
        return None
    if not 1 <= zone <= 60:
        return None
    base = _UTM_DATUM_BASE.get(datum, {}).get(hemi)
    return base + zone if base is not None else None


def utm_epsg(lon: float, lat: float, datum: str = "wgs84") -> int | None:
    """The UTM EPSG code whose zone covers `lon`/`lat` (approximate geographic coordinates),
    computed from the zone formula rather than guessed, so only the geography (which an AI can
    reasonably estimate from place names) is fuzzy, not the zone arithmetic (which it is not
    reliable at, see `steps/translate._maybe_guess_epsg`)."""
    zone = int((lon + 180) // 6) + 1
    if not 1 <= zone <= 60:
        return None
    base = _UTM_DATUM_BASE.get(datum, {}).get("N" if lat >= 0 else "S")
    return base + zone if base is not None else None


def _resolve_mga(text: str) -> int | None:
    m = re.search(r"gda[-\s]?2020.{0,20}(?:mga|zone)\s*(\d{2})", text)
    if m:
        return 7800 + int(m.group(1))
    m = re.search(r"gda[-\s]?94.{0,20}(?:mga|zone)\s*(\d{2})", text)
    if m:
        return 28300 + int(m.group(1))
    return None


def resolve_epsg(source_coordinate_system: str | None, source_coordinate_raw: str | None = None) -> int | None:
    """The EPSG code for the coordinate system described in `source_coordinate_system` and/or
    `source_coordinate_raw` (the zone number is sometimes only in the raw text, e.g. "UTM Sone
    32"), or `None` if it cannot be determined with confidence."""
    haystack = _fold(" ".join(s for s in (source_coordinate_system, source_coordinate_raw) if s))
    if not haystack:
        return None
    mga = _resolve_mga(haystack)
    if mga is not None:
        return mga
    gk = _DHDN_GK.search(haystack)  # checked before the UTM fallback: "zone" alone is a UTM keyword too
    if gk:
        return 31464 + int(gk.group(1) or gk.group(2))
    for named in _NAMED_SYSTEMS:
        if named.pattern.search(haystack):
            return named.epsg
    return _resolve_utm(haystack)


def resolve(borehole: dict) -> None:
    """Fill `borehole["epsg"]` in place from `source_coordinate_system`/`source_coordinate_raw`
    if coordinates are present but the transform step left `epsg` null. No-op otherwise — this
    never touches `x`/`y`, and never overwrites an `epsg` the AI already set."""
    if borehole.get("x") is None or borehole.get("y") is None or borehole.get("epsg") is not None:
        return
    epsg = resolve_epsg(borehole.get("source_coordinate_system"), borehole.get("source_coordinate_raw"))
    if epsg is not None:
        borehole["epsg"] = epsg
