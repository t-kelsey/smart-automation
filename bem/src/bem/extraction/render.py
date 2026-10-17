"""Step 3: validated Borehole -> readable Markdown (borehole table + layer table).

The model never writes Markdown; this is plain string formatting, so the output
is always identical in structure.
"""
from __future__ import annotations

from .schema import Borehole

NA = "n/a"

HEADER_BOREHOLE = ("Borehole", "")
HEADER_LAYERS = ("#", "from [m]", "to [m]", "Stratigraphy", "Petrography", "Colour")


def fmt_num(x: float) -> str:
    """At least one decimal: 112.0 -> '112.0', 24.25 -> '24.25'."""
    s = f"{x:.2f}"
    return s[:-1] if s.endswith("0") else s


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


def render(b: Borehole) -> str:
    def num(x: float | None, unit: str = "m") -> str:
        return f"{fmt_num(x)} {unit}" if x is not None else NA

    def date_(d) -> str:
        return d.strftime("%d.%m.%Y") if d else NA

    stamm = [
        ["Name", b.name],
        ["External ID", b.external_id or NA],
        ["Purpose", b.purpose or NA],
        ["Drilling method", b.drilling_method or NA],
        ["Drilled at", date_(b.drilled_at)],
        ["End date", date_(b.end_date)],
        ["Coordinates", b.source_coordinate_raw or NA],
        ["Coordinate system", b.source_coordinate_system or NA],
        ["Total depth", num(b.total_depth_m)],
        ["Borehole length", num(b.borehole_length_m)],
        ["Elevation", num(b.elevation_m)],
        ["Groundwater level", num(b.groundwater_level_m)],
    ] + [[m.key, m.value] for m in b.metadata]
    layers = [
        [i, fmt_num(l.depth_from_m), fmt_num(l.depth_to_m), l.stratigraphy or NA, l.petrography or NA, l.color or NA]
        for i, l in enumerate(b.layers, 1)
    ]
    return _table(HEADER_BOREHOLE, stamm) + "\n\n" + _table(HEADER_LAYERS, layers) + "\n"
