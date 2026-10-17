"""DIN 4023 glossary and translation of the whole OCR markdown (ADR-0009 to ADR-0012).

Every label and value in the markdown becomes a target:
- labels (table headers, "label: value" lines) resolve to a backend target path (format_keys.py),
- soil and rock values resolve to DIN 4023 designations (Tables 1-3), with colour words added,
- long text is machine-translated (mt.py) without a glossary check,
- numbers and units pass through unchanged,
- single OCR digits inside words are corrected to the letter they replace (ADR-0027),
- comma-separated segments with a token of two or more digits are kept unchanged, as codes; the other segments are translated,
- anything that cannot be translated is kept as translate_error:<original text>.

Keys are lowercase. Main terms give the name and short form of the soil or rock; qualifiers
give the secondary-component form ("sandig, s"). Terms marked AMBIGUOUS need a human decision.
"""

import difflib
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .format_keys import FORMAT_TARGETS, VALUE_KIND, resolve_label

if TYPE_CHECKING:
    from .mt import Translator

log = logging.getLogger(__name__)

# Values up to this many words are looked up in the glossary. Longer text is machine-translated.
MAX_CELL_WORDS = 6

FUZZY_CUTOFF = 0.8

# Numbers with an optional unit, and dash placeholders: values that pass through unchanged.
VALUE_RE = re.compile(
    r"[+\-–]?\d[\d.,]*\s*(?:m|cm|ft|%|°|kpa|mpa|kn/m³|m/s|n|mm)?|[-–—]+",
    re.IGNORECASE,
)

# Dates such as 5/8/14, 05.08.2014 or 2014-08-05: kept unchanged.
DATE_RE = re.compile(r"\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}")

# Value kinds that are kept unchanged; extraction converts them later (ADR-0002, ADR-0004).
PASS_THROUGH_KINDS = {"identifier", "name", "date", "coordinate", "crs", "number"}

# "Label: value" lines outside tables, e.g. "**Borehole No.:** T01".
KEY_VALUE_RE = re.compile(r"^\**(?P<label>[^:*]{2,60}?)\**\s*:\s*\**(?P<value>.+)$")

# Letters that OCR most often reads as a digit inside a word (ADR-0027).
DIGIT_TO_LETTER = {"0": "o", "1": "l", "2": "z", "3": "e", "4": "a", "5": "s", "6": "g", "8": "b"}


@dataclass(frozen=True)
class DinTerm:
    name: str  # DIN 4023 designation (German)
    short: str  # DIN 4023 short form (Kurzform)


@dataclass(frozen=True)
class DinSoil:
    name: str  # e.g. "Schluff, tonig"
    short: str  # e.g. "U, t"


# Main components: Table 1 (soils), Table 2 (rocks), Table 3 (geological names).
MAIN_TERMS: dict[str, DinTerm] = {
    # Table 1, soils
    "large boulder": DinTerm("Großer Block", "gY"),
    "boulder": DinTerm("Block", "Y"),
    "bloque": DinTerm("Block", "Y"),
    "stone": DinTerm("Stein", "X"),
    "cobble": DinTerm("Stein", "X"),
    "gravel": DinTerm("Kies", "G"),
    "kies": DinTerm("Kies", "G"),
    "grus": DinTerm("Kies", "G"),  # Danish/Norwegian "grus" = gravel
    "grava": DinTerm("Kies", "G"),
    "gravier": DinTerm("Kies", "G"),
    "coarse gravel": DinTerm("Grobkies", "gG"),
    "medium gravel": DinTerm("Mittelkies", "mG"),
    "fine gravel": DinTerm("Feinkies", "fG"),
    "sand": DinTerm("Sand", "S"),
    "arena": DinTerm("Sand", "S"),
    "sable": DinTerm("Sand", "S"),
    "coarse sand": DinTerm("Grobsand", "gS"),
    "medium sand": DinTerm("Mittelsand", "mS"),
    "fine sand": DinTerm("Feinsand", "fS"),
    "silt": DinTerm("Schluff", "U"),
    "limo": DinTerm("Schluff", "U"),
    "limon": DinTerm("Schluff", "U"),
    "coarse silt": DinTerm("Grobschluff", "gU"),
    "clay": DinTerm("Ton", "T"),
    "arcilla": DinTerm("Ton", "T"),
    "ler": DinTerm("Ton", "T"),  # Danish "ler" = clay
    "lera": DinTerm("Ton", "T"),
    "argile": DinTerm("Ton", "T"),
    "peat": DinTerm("Torf, Humus", "H"),
    "tørv": DinTerm("Torf, Humus", "H"),  # Danish "tørv" = peat
    "turba": DinTerm("Torf, Humus", "H"),
    "humus": DinTerm("Torf, Humus", "H"),
    "volcanic ash": DinTerm("Vulkanische Aschen", "V"),
    "lignite": DinTerm("Braunkohle", "Bk"),
    "braunkohle": DinTerm("Braunkohle", "Bk"),
    # Table 2, rocks
    "conglomerate": DinTerm("Konglomerat", "Ko"),
    "breccia": DinTerm("Brekzie", "Br"),
    "sandstone": DinTerm("Sandstein", "Sst"),
    "arenisca": DinTerm("Sandstein", "Sst"),
    "siltstone": DinTerm("Schluffstein", "Ust"),
    "claystone": DinTerm("Tonstein", "Tst"),
    "mudstone": DinTerm("Tonstein", "Tst"),
    "marlstone": DinTerm("Mergelstein", "Mst"),
    "marl": DinTerm("Mergelstein", "Mst"),
    "marga": DinTerm("Mergelstein", "Mst"),
    "limestone": DinTerm("Kalkstein", "Kst"),
    "caliza": DinTerm("Kalkstein", "Kst"),
    "kalk": DinTerm("Kalkstein", "Kst"),  # AMBIGUOUS in Danish: chalk (Kreidestein) or limestone
    "dolomite": DinTerm("Dolomitstein", "Dst"),
    "anhydrite": DinTerm("Anhydrit", "Ahst"),
    "gypsum": DinTerm("Gips", "Gyst"),
    "yeso": DinTerm("Gips", "Gyst"),
    "rock salt": DinTerm("Salzgestein", "Sast"),
    "tuff": DinTerm("Tuffstein", "Vst"),
    "hard coal": DinTerm("Steinkohle", "Stk"),
    "steinkohle": DinTerm("Steinkohle", "Stk"),
    "quartzite": DinTerm("Quarzit", "Q"),
    "basalt": DinTerm("Vulkanite (z. B. Basalt)", "Vu"),
    "granite": DinTerm("Plutonite (z. B. Granit)", "Pl"),
    "gneiss": DinTerm("Massige Metamorphite (z. B. Gneis)", "Mem"),
    "schist": DinTerm("Blättrige, feinschichtige Metamorphite (z. B. Glimmerschiefer)", "Meb"),
    # Table 3, geological names
    "topsoil": DinTerm("Oberboden (Mutterboden)", "Mu"),
    "fill": DinTerm("Anthropogene Böden", "A"),
    "relleno": DinTerm("Anthropogene Böden", "A"),
    "fyld": DinTerm("Anthropogene Böden", "A"),
    "weathered loam": DinTerm("Verwitterungslehm, Hanglehm", "L"),
    "slope debris": DinTerm("Hangschutt", "Lx"),
    "glacial till": DinTerm("Geschiebelehm", "Lg"),
    "loess": DinTerm("Löß", "Lö"),
    "loess loam": DinTerm("Lößlehm", "Löl"),
    "varved clay": DinTerm("Bänderton", "Bt"),
    "chalk": DinTerm("Kreidestein", "Krst"),
    "tufa": DinTerm("Kalktuff", "Ktst"),
}

# Secondary components: adjectives for the Nebenanteil, Table 1 and 4.2.2.
QUALIFIERS: dict[str, DinTerm] = {
    "sandy": DinTerm("sandig", "s"),
    "arenoso": DinTerm("sandig", "s"),
    "arenosa": DinTerm("sandig", "s"),
    "sandet": DinTerm("sandig", "s"),
    "gravelly": DinTerm("kiesig", "g"),
    "gravoso": DinTerm("kiesig", "g"),
    "gruset": DinTerm("kiesig", "g"),
    "silty": DinTerm("schluffig", "u"),
    "limoso": DinTerm("schluffig", "u"),
    "limosa": DinTerm("schluffig", "u"),
    "clayey": DinTerm("tonig", "t"),
    "arcilloso": DinTerm("tonig", "t"),
    "leret": DinTerm("tonig", "t"),
    "organic": DinTerm("humos", "h"),
    "peaty": DinTerm("torfig", "h"),
}

# Colours (Soil/Rockprofile, color/pattern). Names follow the colour words of DIN 4023
# Tables 1-3 and Annex A. Where DIN has no word, the nearest German colour name is used.
# Base colours name the colour; tints ("rojizo", "amarillento") are added in front of it.
COLOUR_BASE: dict[str, str] = {
    "castaño": "braun", "castano": "braun", "marrón": "braun", "marron": "braun",
    "brown": "braun", "braun": "braun", "brun": "braun", "brunt": "braun",
    "gris": "grau", "gray": "grau", "grey": "grau", "grau": "grau", "grå": "grau",
    "negro": "schwarz", "black": "schwarz", "schwarz": "schwarz", "sort": "schwarz", "svart": "schwarz",
    "blanco": "weiß", "white": "weiß", "hvid": "weiß", "weiß": "weiß",
    "rojo": "rot", "red": "rot", "rot": "rot", "rød": "rot",
    "amarillo": "gelb", "yellow": "gelb", "gelb": "gelb", "gul": "gelb",
    "verde": "grün", "green": "grün", "grün": "grün", "grønn": "grün", "grønt": "grün",
    "azul": "blau", "blue": "blau", "blau": "blau", "blå": "blau",
    "naranja": "orange", "orange": "orange",
    "oliva": "oliv", "olive": "oliv", "oliv": "oliv",
    "violeta": "violett", "violett": "violett", "lila": "lila", "purple": "violett",
    "rosa": "rosa", "pink": "rosa",
}
COLOUR_TINT: dict[str, str] = {
    "rojizo": "rot", "reddish": "rot", "rødlig": "rot",
    "amarillento": "gelb", "yellowish": "gelb", "gulig": "gelb",
    "verdoso": "grün", "greenish": "grün", "grønlig": "grün",
    "azulado": "blau", "bluish": "blau", "blåligt": "blau",
    "grisáceo": "grau", "grisaceo": "grau", "greyish": "grau", "gråligt": "grau",
}
COLOUR_LIGHTNESS: dict[str, str] = {
    "claro": "hell", "light": "hell", "clair": "hell", "lys": "hell", "ljus": "hell", "hell": "hell",
    "oscuro": "dunkel", "dark": "dunkel", "foncé": "dunkel", "mørk": "dunkel", "dunkel": "dunkel",
}

# Source abbreviations written out before lookup. Matched as whole words and case-sensitive,
# because the USCS codes (CL, ML) and log abbreviations (Cl, Si) are written that way.
ABBREVIATIONS: dict[str, str] = {
    # USCS group symbols
    "GW": "gravel", "GP": "gravel", "GM": "silty gravel", "GC": "clayey gravel",
    "SW": "sand", "SP": "sand", "SM": "silty sand", "SC": "clayey sand",
    "ML": "silt", "MH": "silt", "CL": "clay", "CH": "clay",
    "OL": "organic silt", "OH": "organic clay", "Pt": "peat",
    # Common log abbreviations
    "Sa": "sand", "Gr": "gravel", "Cl": "clay", "Si": "silt", "LS": "limestone", "SS": "sandstone",
}

# DIN short forms back to their designations, for cells that only contain codes ("U, t").
# Where two terms share a short form, the first one listed wins (e.g. "h" is humos).
DIN_SHORT_MAIN: dict[str, str] = {}
for _term in MAIN_TERMS.values():
    DIN_SHORT_MAIN.setdefault(_term.short, _term.name)
DIN_SHORT_QUALIFIERS: dict[str, str] = {}
for _term in QUALIFIERS.values():
    DIN_SHORT_QUALIFIERS.setdefault(_term.short, _term.name)

# Single-word glossary keys, the candidates for fuzzy correction of misspelt words.
SINGLE_WORD_KEYS = [key for key in (*MAIN_TERMS, *QUALIFIERS) if " " not in key]


def _find_main(text: str) -> tuple[int, DinTerm] | None:
    """Earliest main term in the text. Longer keys win when two start at the same place."""
    best: tuple[int, int, DinTerm] | None = None
    for key, term in MAIN_TERMS.items():
        match = re.search(rf"\b{re.escape(key)}\b", text)
        if match and (best is None or (match.start(), -len(key)) < (best[0], -best[1])):
            best = (match.start(), len(key), term)
    return (best[0], best[2]) if best else None


def translate_term(text: str) -> DinSoil | None:
    """Translate a soil or rock phrase to its DIN 4023 name and short form.

    Returns None when no main term is recognised, so the caller can try the next stage.
    """
    lowered = text.lower()
    found = _find_main(lowered)
    if found is None:
        return None
    _, main = found

    qualifiers: list[DinTerm] = []
    for key, term in QUALIFIERS.items():
        if re.search(rf"\b{re.escape(key)}\b", lowered) and term not in qualifiers:
            qualifiers.append(term)

    name = ", ".join([main.name, *(q.name for q in qualifiers)])
    short = ", ".join([main.short, *(q.short for q in qualifiers)])
    return DinSoil(name=name, short=short)


def translate_colour(text: str) -> str | None:
    """Translate colour words in the cell to a DIN colour name, e.g. "hellrotbraun".

    Lightness comes first, then the tint, then the base colour, as in German compounds.
    Returns None if the cell has no colour words.
    """
    words = re.findall(r"[^\W\d_]+", text.lower())
    base = next((COLOUR_BASE[w] for w in words if w in COLOUR_BASE), None)
    tint = next((COLOUR_TINT[w] for w in words if w in COLOUR_TINT), None)
    lightness = next((COLOUR_LIGHTNESS[w] for w in words if w in COLOUR_LIGHTNESS), "")

    if base is None:
        # A tint alone ("verdoso amarillento") still names a colour: the first tint is the base.
        base, tint = tint, None
    if base is None:
        return None
    if tint == base:
        tint = None
    return lightness + (tint or "") + base


def expand_abbreviations(text: str) -> str:
    for abbreviation, full in ABBREVIATIONS.items():
        text = re.sub(rf"\b{re.escape(abbreviation)}\b", full, text)
    return text


def expand_din_codes(text: str) -> str | None:
    """Return the designation for a cell made only of DIN short forms ("U, t"), else None."""
    parts = [part.strip() for part in text.split(",")]
    names: list[str] = []
    for i, part in enumerate(parts):
        if i == 0 and part in DIN_SHORT_MAIN:
            names.append(DIN_SHORT_MAIN[part])
        elif i > 0 and part in DIN_SHORT_QUALIFIERS:
            names.append(DIN_SHORT_QUALIFIERS[part])
        else:
            return None
    return ", ".join(names)


def fuzzy_correct(text: str) -> str:
    """Replace each word with its closest glossary key, if one is close enough."""

    def correct(match: re.Match) -> str:
        word = match.group(0)
        if len(word) < 4:
            return word
        close = difflib.get_close_matches(word.lower(), SINGLE_WORD_KEYS, n=1, cutoff=FUZZY_CUTOFF)
        return close[0] if close else word

    return re.sub(r"[^\W\d_]+", correct, text)


def _resolve_soil(expanded: str, src: str, translator: "Translator | None") -> str | None:
    """Soil designation for an abbreviation-expanded cell, or None if no stage finds one."""
    codes = expand_din_codes(expanded)
    if codes:
        return codes

    for candidate in (expanded, fuzzy_correct(expanded)):
        soil = translate_term(candidate)
        if soil:
            return soil.name

    if src != "en" and translator is not None:
        english = translator.translate(expanded, src)
        if english:
            soil = translate_term(expand_abbreviations(english))
            if soil:
                return soil.name
    return None


def resolve_cell(text: str, src: str, translator: "Translator | None") -> str:
    """Translate one short value to a DIN 4023 designation, or to translate_error:<text>.

    Stages, in order: abbreviations written out, DIN short forms, glossary, fuzzy correction,
    machine translation to English and glossary again. A result is only used if it hits a
    glossary entry. Colour words in the cell are added as "; Farbe: <colour>".
    """
    original = text.strip()
    soil_name = _resolve_soil(expand_abbreviations(original), src, translator)
    if soil_name is None:
        return f"translate_error:{original}"

    colour = translate_colour(original)
    if colour:
        return f"{soil_name}; Farbe: {colour}"
    return soil_name


def _record(result: str, errors: list[str]) -> str:
    """Keep a translation result, and note it in errors if it is a translate_error."""
    if result.startswith("translate_error:"):
        errors.append(result)
    return result


def _translate_free(
    text: str, src: str, translator: "Translator | None", errors: list[str], original: str | None = None
) -> str:
    """Machine-translate long text to English. English text is already in the target language."""
    if src == "en":
        return text
    english = translator.translate(text, src) if translator is not None else None
    return _record(english or f"translate_error:{original or text}", errors)


def _has_code(text: str) -> bool:
    """True if a token has two or more digits. Such tokens are codes or measurements, not words."""
    return any(sum(char.isdigit() for char in token) >= 2 for token in text.split())


def _fix_ocr_digits(text: str) -> str:
    """Replace a single digit inside a word with the letter OCR probably misread (ADR-0027).

    Tokens with two or more digits, and tokens with one digit and fewer than three letters,
    are kept unchanged.
    """

    def fix(match: re.Match) -> str:
        token = match.group(0)
        digits = sum(char.isdigit() for char in token)
        letters = sum(char.isalpha() for char in token)
        if digits == 1 and letters >= 3:
            return "".join(DIGIT_TO_LETTER.get(char, char) for char in token) # type: ignore
        return token

    return re.sub(r"\S+", fix, text)


def _translate_plain(text: str, kind: str, src: str, translator: "Translator | None", errors: list[str]) -> str:
    """Translate a value that has no codes in it, after correcting OCR digits in its words."""
    fixed = _fix_ocr_digits(text)
    if kind == "colour":
        return _record(translate_colour(fixed) or f"translate_error:{text}", errors)
    if kind == "text" or len(fixed.split()) > MAX_CELL_WORDS:
        return _translate_free(fixed, src, translator, errors, original=text)
    result = resolve_cell(fixed, src, translator)
    if result.startswith("translate_error:"):
        result = f"translate_error:{text}"
    return _record(result, errors)


def _translate_value(text: str, kind: str, src: str, translator: "Translator | None", errors: list[str]) -> str:
    """Translate one value by the kind of its target (format_keys.VALUE_KIND).

    In a comma-separated value, segments with a code ("10-12 m") are kept as written and the
    other segments are translated, so "Sand, 10-12 m" becomes "Sand, 10-12 m" with Sand translated.
    """
    stripped = text.strip()
    if not stripped or kind in PASS_THROUGH_KINDS or VALUE_RE.fullmatch(stripped) or DATE_RE.fullmatch(stripped):
        return stripped
    if not _has_code(stripped):
        return _translate_plain(stripped, kind, src, translator, errors)
    parts = [part.strip() for part in stripped.split(",") if part.strip()]
    return ", ".join(
        part if _has_code(part) else _translate_plain(part, kind, src, translator, errors) for part in parts
    )


def _translate_header(text: str, src: str, translator: "Translator | None", errors: list[str]) -> tuple[str, str | None]:
    """Target path for a header, and its format key. A header that finds no key is an error."""
    stripped = text.strip()
    if _has_code(stripped):
        return stripped, None
    key = resolve_label(_fix_ocr_digits(stripped), src, translator)
    if key is None:
        return _record(f"translate_error:{stripped}", errors), None
    return FORMAT_TARGETS[key], key


def translate_markdown(markdown: str, src: str, translator: "Translator | None") -> tuple[str, list[str]]:
    """Translate the whole markdown: tables, "label: value" lines and free text.

    Returns the translated markdown and every translate_error it contains.
    """
    lines = markdown.splitlines()
    out: list[str] = []
    errors: list[str] = []

    i = 0
    while i < len(lines):
        if not _is_row(lines[i]):
            out.append(_translate_line(lines[i], src, translator, errors))
            i += 1
            continue
        block: list[str] = []
        while i < len(lines) and _is_row(lines[i]):
            block.append(lines[i])
            i += 1
        out.extend(_translate_table(block, src, translator, errors))

    if errors:
        log.warning("%d values could not be translated (marked translate_error)", len(errors))
    return "\n".join(out), errors


def _translate_table(block: list[str], src: str, translator: "Translator | None", errors: list[str]) -> list[str]:
    """Translate one markdown table. The first row is the header when a separator row follows it.

    Each body cell takes the value kind of its header's key. A column whose header is an error
    keeps its cells unchanged; the header error is already recorded.
    """
    rows = [line.split("|") for line in block]
    has_header = len(block) > 1 and _is_separator(rows[1])
    column_kinds: dict[int, str] = {}

    out: list[str] = []
    for index, (line, cells) in enumerate(zip(block, rows)):
        if _is_separator(cells):
            out.append(line)
            continue
        for i, cell in enumerate(cells):
            if not cell.strip():
                continue
            if has_header and index == 0:
                target, key = _translate_header(cell, src, translator, errors)
                if key is not None:
                    column_kinds[i] = VALUE_KIND[key]
                cells[i] = f" {target} "
            elif not has_header:
                cells[i] = f" {_translate_value(cell, 'soil', src, translator, errors)} "
            elif i in column_kinds:
                cells[i] = f" {_translate_value(cell, column_kinds[i], src, translator, errors)} "
        out.append("|".join(cells))
    return out


def _translate_line(line: str, src: str, translator: "Translator | None", errors: list[str]) -> str:
    stripped = line.strip()
    if (
        not stripped
        or stripped.startswith("#")
        or VALUE_RE.fullmatch(stripped)
        or any(char.isdigit() for char in stripped)
    ):
        return line

    match = KEY_VALUE_RE.match(stripped)
    if match:
        key = resolve_label(match.group("label"), src, translator)
        if key is not None:
            value = _translate_value(match.group("value"), VALUE_KIND[key], src, translator, errors)
            return f"{FORMAT_TARGETS[key]}: {value}"
    return _translate_free(stripped, src, translator, errors)


def _is_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def _is_separator(cells: list[str]) -> bool:
    return all(not cell.strip() or set(cell.strip()) <= set("-:") for cell in cells)
