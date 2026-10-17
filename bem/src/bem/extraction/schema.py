"""Schema of the Qwen output: one borehole with its layers, shaped like the backend.

Field names match `boreholes` / `borehole_layers` (docs/elixir-backend-borehole-pipeline.md,
ADR-0012, ADR-0023), so `Borehole.to_api_dict()` can be sent to the API as it is.

All fields are required-but-nullable on purpose: with constrained decoding the model
must emit every key, and has to say "null" instead of silently leaving a field out.

Not extracted, because the backend sets them: `id`, `location` (PostGIS reprojects the raw
coordinate, ADR-0002), `verified` (a human sets it) and the layer `position` (added here,
after sorting by depth).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # -> additionalProperties: false


class MetadataItem(_Strict):
    # A list of key/value pairs instead of a free dict, because strict constrained decoding
    # does not allow open objects. `to_api_dict()` turns the list into the jsonb map.
    key: str = Field(description="Short English label, e.g. 'contractor', 'rig', 'driller', 'rqd_percent'")
    value: str = Field(description="Value exactly as written in the text")


class Layer(_Strict):
    depth_from_m: float = Field(description="Top of the layer in metres below ground")
    depth_to_m: float = Field(description="Bottom of the layer in metres below ground")
    stratigraphy: Optional[str] = Field(description="Geological formation / age, as written; null if not stated")
    petrography: Optional[str] = Field(description="Rock or soil description, as written; null if not stated")
    color: Optional[str] = Field(description="Colour of the layer, as written; null if not stated")
    raw_text: Optional[str] = Field(description="The source text of this layer's row, copied verbatim")
    metadata: List[MetadataItem] = Field(description="Per-layer values with no own field (e.g. RQD, SPT); [] if none")


class Borehole(_Strict):
    name: str = Field(description="Name of the borehole, e.g. 'BH 2'")
    external_id: Optional[str] = Field(description="ID assigned by the project or source, e.g. 'BH_AB01'; null if absent")
    purpose: Optional[str] = Field(description="Purpose of the borehole; null if not stated")
    drilling_method: Optional[str] = Field(description="Drilling method; null if not stated")
    drilled_at: Optional[date] = Field(description="Start date of drilling, ISO format YYYY-MM-DD")
    end_date: Optional[date] = Field(description="Completion date, ISO format YYYY-MM-DD")
    source_coordinate_system: Optional[str] = Field(description="Coordinate system as written, e.g. '32U UTM', 'EPSG:25832'")
    source_coordinate_raw: Optional[str] = Field(description="Coordinates exactly as written, e.g. 'E 123456 N 5432100'")
    total_depth_m: Optional[float] = Field(description="Final depth (vertical) in metres")
    borehole_length_m: Optional[float] = Field(description="Length along the hole axis in metres, only if stated")
    elevation_m: Optional[float] = Field(description="Collar elevation in metres above sea level")
    groundwater_level_m: Optional[float] = Field(description="Depth to groundwater below surface in metres")
    metadata: List[MetadataItem] = Field(description="Other borehole values with no own field (contractor, rig, driller, ...); [] if none")
    layers: List[Layer] = Field(description="All layers, one entry each, in depth order")

    def to_api_dict(self) -> dict:
        """The record in the backend's shape: metadata as maps, layers numbered by position."""
        data = self.model_dump(mode="json", exclude={"layers", "metadata"})
        data["metadata"] = {m.key: m.value for m in self.metadata}
        data["verified"] = False
        data["layers"] = []
        for position, layer in enumerate(self.layers, 1):
            item = layer.model_dump(mode="json", exclude={"metadata"})
            item["position"] = position
            item["metadata"] = {m.key: m.value for m in layer.metadata}
            data["layers"].append(item)
        return data
