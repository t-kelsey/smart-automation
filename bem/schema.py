"""Pydantic models for the per-borehole JSON sent to the Elixir API (ADR-0004, ADR-0005).

Fields follow Standards_Formats/BoreholeDataFormat.xlsx. Coordinates are passed through
raw with an EPSG code; PostGIS reprojects them (ADR-0002).
"""

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    depth_from_m: float | None = None
    depth_to_m: float | None = None
    lithology: str | None = None
    stratigraphic_name: str | None = None
    geologic_age: str | None = None
    groundwater_level_m: float | None = None
    spt: int | None = None
    rqd_percent: float | None = None
    core_recovery_percent: float | None = None


class Borehole(BaseModel):
    source_file: str
    borehole_id: str | None = None
    project_name: str | None = None
    location_name: str | None = None
    x: float | None = None
    y: float | None = None
    epsg: int | None = None
    surface_elevation_masl: float | None = None
    borehole_depth_m: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    log: list[LogEntry] = Field(default_factory=list)
    # The translated markdown this record was built from. Kept for review and for
    # fields we couldn't map yet (ADR-0005).
    raw_markdown: str = ""
    # Values in this borehole's section that could not be translated (translate_error:...).
    # The API should keep the record unverified until these are resolved (ADR-0020).
    translate_errors: list[str] = Field(default_factory=list)
