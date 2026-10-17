"""Schema for one borehole record (matches bohrhole_template.md).

All fields are required-but-nullable on purpose: with constrained decoding the model
must emit every key, and has to say "null" instead of silently leaving a field out.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # -> additionalProperties: false


class Koordinaten(_Strict):
    zone: Optional[str] = Field(description="UTM zone exactly as written, e.g. '32U'")
    ost: Optional[float] = Field(description="Rechtswert / easting, exactly as written")
    nord: Optional[float] = Field(description="Hochwert / northing, exactly as written")


class Schicht(_Strict):
    von_m: float = Field(description="Top of the layer in metres below ground")
    bis_m: float = Field(description="Bottom of the layer in metres below ground")
    stratigraphie: str = Field(description="Stratigraphic unit, original wording; 'keine Angabe' if missing")
    petrographie: str = Field(description="Rock description, original wording; 'keine Angabe' if missing")


class Bohrung(_Strict):
    aufschlussname: str = Field(description="Name of the borehole / Aufschluss")
    bohrzweck: str = Field(description="Purpose of the borehole; 'Unbekannt' if not stated")
    bohrart: str = Field(description="Drilling type; 'Unbekannt' if not stated")
    bohrdatum: Optional[date] = Field(description="Drilling date, ISO format YYYY-MM-DD")
    koordinaten: Koordinaten
    endteufe_m: Optional[float] = Field(description="Final depth in metres")
    ansatzhoehe_m: Optional[float] = Field(description="Collar elevation in metres above sea level (m ü. NN)")
    lgrb_geprueft: Optional[bool] = Field(description="true/false only if the text states it, else null")
    schichten: List[Schicht] = Field(description="All layers, one entry each, in depth order")
