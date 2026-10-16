"""Translate OCR'd/extracted text and map it onto the borehole data format.

Target fields follow Standards_Formats/BoreholeDataFormat.xlsx. Coordinates are
passed through raw with an EPSG code; PostGIS reprojects them (ADR-0002).
"""

from dataclasses import dataclass, field

from .triage import Document


@dataclass
class LogEntry:
    depth_from_m: float | None = None
    depth_to_m: float | None = None
    lithology: str | None = None
    stratigraphic_name: str | None = None
    geologic_age: str | None = None
    groundwater_level_m: float | None = None
    spt: int | None = None
    rqd_percent: float | None = None
    core_recovery_percent: float | None = None


@dataclass
class Borehole:
    source_file: str
    borehole_name: str | None = None
    project_name: str | None = None
    location_name: str | None = None
    x: float | None = None
    y: float | None = None
    epsg: int | None = None
    surface_elevation_masl: float | None = None
    borehole_depth_m: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    log: list[LogEntry] = field(default_factory=list)


def translate(text: str) -> str:
    # TODO: pick a translation backend (target language: English).
    return text


def extract(doc: Document) -> list[Borehole]:
    text = translate("\n\n".join(p.text or "" for p in doc.pages))
    # TODO: map text onto Borehole/LogEntry fields; convert ft to m.
    return [Borehole(source_file=doc.source.name, borehole_name=doc.borehole_id)] if text.strip() else []
