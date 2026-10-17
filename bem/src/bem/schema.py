"""Pydantic models for the per-borehole JSON sent to the Elixir API (ADR-0004, ADR-0005).

Field names and types mirror the Ecto schemas in api/lib/api/boreholes/ (boreholes and
borehole_layers columns, the `metadata` maps, and the `borehole_layers` association).
Fields that only the pipeline needs (source_file, raw_markdown, translate_errors) are
kept on the model for review; the sink folds them into `metadata` (ADR-0005, ADR-0020).
Coordinates are passed through raw with the coordinate system name (ADR-0002).
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class BoreholeLayer(BaseModel):
    """One row of borehole_layers. depth_to_m must be greater than depth_from_m (API changeset)."""

    position: int
    depth_from_m: float
    depth_to_m: float
    stratigraphy: str | None = None
    petrography: str | None = None
    color: str | None = None
    # Original OCR text for this row, kept for QA (ADR-0005).
    raw_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Borehole(BaseModel):
    """One row of boreholes, with its layers. `name` is required by the API."""

    name: str
    external_id: str | None = None
    purpose: str | None = None
    drilling_method: str | None = None
    drilled_at: date | None = None
    end_date: date | None = None
    source_coordinate_system: str | None = None
    source_coordinate_raw: str | None = None
    total_depth_m: float | None = None
    borehole_length_m: float | None = None
    elevation_m: float | None = None
    groundwater_level_m: float | None = None
    # The API keeps every extracted record unverified until a human has reviewed it.
    verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    borehole_layers: list[BoreholeLayer] = Field(default_factory=list)

    # Pipeline-only provenance (ADR-0005). Not API columns.
    source_file: str
    # The translated markdown this record was built from.
    raw_markdown: str = ""
    # Values in this borehole's section that could not be translated (translate_error:...).
    # The API should keep the record unverified until these are resolved (ADR-0020).
    translate_errors: list[str] = Field(default_factory=list)
