"""Step 3: validated Bohrung -> Markdown in the format of bohrhole_template.md.

The model never writes Markdown; this is plain string formatting, so the output
is always identical in structure.
"""
from __future__ import annotations

from .schema import Bohrung

NA = "keine Angabe"

# Headers copied 1:1 from bohrhole_template.md (including "bis" without unit and
# "Stratigraphi"). Change them here if you want cleaned-up headers.
HEADER_STAMMDATEN = ("Stammdaten", "")
HEADER_SCHICHTEN = ("#", "von [m]", "bis", "Stratigraphi", "Petrographie")


def fmt_num(x: float) -> str:
    """German decimal comma, at least one decimal: 112.0 -> '112,0', 24.25 -> '24,25'."""
    s = f"{x:.2f}"
    if s.endswith("0"):
        s = s[:-1]
    return s.replace(".", ",")


def _esc(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _table(header: tuple[str, ...], rows: list[list[object]]) -> str:
    head = [_esc(c) for c in header]
    body = [[_esc(c) for c in r] for r in rows]
    widths = [max([len(head[i]), 4] + [len(r[i]) for r in body]) for i in range(len(head))]

    def line(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    return "\n".join([line(head), sep] + [line(r) for r in body])


def _koordinaten(b: Bohrung) -> str:
    k = b.koordinaten
    if k.ost is None and k.nord is None:
        return NA
    ost = repr(k.ost) if k.ost is not None else NA
    nord = repr(k.nord) if k.nord is not None else NA
    return f"{k.zone or ''} O: {ost} | N: {nord}".strip()


def render(b: Bohrung) -> str:
    stamm = [
        ["Aufschlussname", b.aufschlussname],
        ["Bohrzweck", b.bohrzweck],
        ["Bohrart", b.bohrart],
        ["Bohrdatum", b.bohrdatum.strftime("%d.%m.%Y") if b.bohrdatum else NA],
        ["Koordinaten", _koordinaten(b)],
        ["Endteufe", f"{fmt_num(b.endteufe_m)} m" if b.endteufe_m is not None else NA],
        ["Ansatzhöhe", f"{fmt_num(b.ansatzhoehe_m)} m ü. NN" if b.ansatzhoehe_m is not None else NA],
        ["LGRB geprüft", {True: "Ja", False: "Nein", None: NA}[b.lgrb_geprueft]],
    ]
    schichten = [
        [i, fmt_num(l.von_m), fmt_num(l.bis_m), l.stratigraphie, l.petrographie]
        for i, l in enumerate(b.schichten, 1)
    ]
    return _table(HEADER_STAMMDATEN, stamm) + "\n\n" + _table(HEADER_SCHICHTEN, schichten) + "\n"
