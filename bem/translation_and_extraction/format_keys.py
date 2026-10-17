"""Format keys from BoreholeDataFormat.xlsx, each mapped to its backend target and value kind (ADR-0012).

FORMAT_TARGETS gives the target path for each key in the xlsx. Paths follow
docs/elixir-backend-borehole-pipeline.md: fixed columns where the backend has one, and
`metadata.<key>` for values without a column. Layer values go to `borehole_layers`, and
borehole values to `boreholes`, so the split step can route each value to its table.

VALUE_KIND says how a value under that key is translated (see din4023.py):
- identifier, name, date, coordinate, crs, number: kept unchanged (extraction converts them, ADR-0002/0004)
- soil: DIN 4023 soil and rock term (ADR-0009)
- colour: colour words only
- text: free text, machine-translated

FORMAT_LABELS gives the source-language labels that appear as table headers or
"label: value" lines in the logs (lowercase; en, es, da/no, de, fr).
"""

import difflib
import re

# Layer depth columns are not keys in the xlsx; the layer table needs them (ADR-0012).
FORMAT_TARGETS: dict[str, str] = {
    "BoreholeID": "boreholes.external_id",
    "BoreholeName": "boreholes.name",
    "ProjectID": "boreholes.metadata.project_id",
    "ProjectName": "boreholes.metadata.project_name",
    "LocationName": "boreholes.metadata.location_name",
    "StartDate": "boreholes.drilled_at",
    "EndDate": "boreholes.end_date",
    "Surface Elevation": "boreholes.elevation_m",
    "X-Coordinate": "boreholes.source_coordinate_raw.x",
    "Y-Coordinate": "boreholes.source_coordinate_raw.y",
    "CoordinateSystem": "boreholes.source_coordinate_system",
    "BoreholeDepth": "boreholes.total_depth_m",
    "BoreholeLength": "boreholes.borehole_length_m",
    "Notes": "boreholes.metadata.notes",
    "Groundwaterlevel": "boreholes.groundwater_level_m",
    "StratigraphicName": "borehole_layers.stratigraphy",
    "GeologicAge": "borehole_layers.metadata.geologic_age",
    "EngineeringSoilUnit": "borehole_layers.metadata.engineering_soil_unit",
    "Lithology/SoilName": "borehole_layers.petrography",
    "Soil/Rockprofile": "borehole_layers.color",
    "Core": "borehole_layers.metadata.core",
    "SampleName": "borehole_layers.metadata.sample_name",
    "SampleDepth": "borehole_layers.metadata.sample_depth_m",
    "TotalCoreRecovery": "borehole_layers.metadata.total_core_recovery_pct",
    "RQD": "borehole_layers.metadata.rqd_pct",
    "SPT": "borehole_layers.metadata.spt_n",
    "Watercontent": "borehole_layers.metadata.water_content_pct",
    "Cosistency": "borehole_layers.metadata.consistency",  # spelling as in the xlsx
    "UCS": "borehole_layers.metadata.ucs_mpa",
    "Tensile strength": "borehole_layers.metadata.tensile_strength_mpa",
    "Unitweight": "borehole_layers.metadata.unit_weight_kn_m3",
    "CAI": "borehole_layers.metadata.cerchar_index",
    "RMR": "borehole_layers.metadata.rmr",
    "Q": "borehole_layers.metadata.q",
    "GSI": "borehole_layers.metadata.gsi",
    "FrictionAngle": "borehole_layers.metadata.friction_angle_deg",
    "Cohesion": "borehole_layers.metadata.cohesion_kpa",
    "Grainsize-fines": "borehole_layers.metadata.grain_size_fines_pct",
    "LiquidLimit": "borehole_layers.metadata.liquid_limit_pct",
    "PlasticityLimit": "borehole_layers.metadata.plasticity_limit_pct",
    "PlasticityIndex": "borehole_layers.metadata.plasticity_index",
    "ConsistencyIndex": "borehole_layers.metadata.consistency_index",
    "HydraulicCoefficient": "borehole_layers.metadata.hydraulic_coefficient_m_s",
    "E-Modulus": "borehole_layers.metadata.e_modulus_mpa",
    "PoissonsRatio": "borehole_layers.metadata.poissons_ratio",
    # Not xlsx keys: layer top and bottom depth, from the layer table (ADR-0012).
    "LayerDepthFrom": "borehole_layers.depth_from_m",
    "LayerDepthTo": "borehole_layers.depth_to_m",
}

VALUE_KIND: dict[str, str] = {
    "BoreholeID": "identifier",
    "BoreholeName": "name",
    "ProjectID": "identifier",
    "ProjectName": "name",
    "LocationName": "name",
    "StartDate": "date",
    "EndDate": "date",
    "Surface Elevation": "number",
    "X-Coordinate": "coordinate",
    "Y-Coordinate": "coordinate",
    "CoordinateSystem": "crs",
    "BoreholeDepth": "number",
    "BoreholeLength": "number",
    "Notes": "text",
    "Groundwaterlevel": "number",
    "StratigraphicName": "text",
    "GeologicAge": "text",
    "EngineeringSoilUnit": "text",
    "Lithology/SoilName": "soil",
    "Soil/Rockprofile": "colour",
    "Core": "text",
    "SampleName": "identifier",
    "SampleDepth": "number",
    "TotalCoreRecovery": "number",
    "RQD": "number",
    "SPT": "number",
    "Watercontent": "number",
    "Cosistency": "text",
    "UCS": "number",
    "Tensile strength": "number",
    "Unitweight": "number",
    "CAI": "number",
    "RMR": "number",
    "Q": "number",
    "GSI": "number",
    "FrictionAngle": "number",
    "Cohesion": "number",
    "Grainsize-fines": "number",
    "LiquidLimit": "number",
    "PlasticityLimit": "number",
    "PlasticityIndex": "number",
    "ConsistencyIndex": "number",
    "HydraulicCoefficient": "number",
    "E-Modulus": "number",
    "PoissonsRatio": "number",
    "LayerDepthFrom": "number",
    "LayerDepthTo": "number",
}

if set(VALUE_KIND) != set(FORMAT_TARGETS):
    raise RuntimeError("VALUE_KIND and FORMAT_TARGETS must cover the same keys")

FORMAT_LABELS: dict[str, list[str]] = {
    "BoreholeID": ["borehole id", "borehole no", "borehole number", "hole no", "hole number", "sondeo nº", "bohrung nr", "boring nr"],
    "BoreholeName": ["borehole name", "hole name"],
    "ProjectID": ["project id", "project no", "projekt nr"],
    "ProjectName": ["project", "project name", "proyecto", "projekt", "prosjekt"],
    "LocationName": ["location", "location name", "lokation", "lokalitet", "ubicación", "standort"],
    "StartDate": ["start date", "date started", "fecha inicio", "startdato", "anfangsdatum"],
    "EndDate": ["end date", "date completed", "fecha fin", "slutdato", "enddatum"],
    "Surface Elevation": ["surface elevation", "ground level", "elevation", "cota", "kote", "ansatzhöhe"],
    "X-Coordinate": ["x", "x-coordinate", "easting", "este", "øst", "rechtswert"],
    "Y-Coordinate": ["y", "y-coordinate", "northing", "norte", "nord", "hochwert"],
    "CoordinateSystem": ["coordinate system", "crs", "sistema de coordenadas", "koordinatsystem"],
    "BoreholeDepth": ["total depth", "borehole depth", "final depth", "endteufe", "profundidad total", "total dybde"],
    "BoreholeLength": ["borehole length", "hole length"],
    "Notes": ["notes", "remarks", "comments", "bemerkungen", "observaciones", "bemærkninger"],
    "Groundwaterlevel": ["groundwater", "groundwater level", "water level", "grundwasser", "nivel freático", "grundvandsspejl", "grunnvann"],
    "StratigraphicName": ["stratigraphy", "stratigraphic name", "stratigraphie", "estratigrafía", "stratigrafi"],
    "GeologicAge": ["geologic age", "geological age", "geologisches alter", "edad geológica", "alder"],
    "EngineeringSoilUnit": ["engineering soil unit", "soil unit", "bodenklasse"],
    "Lithology/SoilName": ["lithology", "soil name", "soil description", "petrography", "litología", "descripción", "lithologie", "beschreibung", "litologi", "jordart"],
    "Soil/Rockprofile": ["color", "colour", "color/pattern", "colour/pattern", "farbe", "farve", "farge"],
    "Core": ["core", "core sample", "kern", "testigo"],
    "SampleName": ["sample", "sample name", "sample no", "probe", "muestra", "prøve"],
    "SampleDepth": ["sample depth", "depth of sample", "probentiefe", "profundidad de muestra", "prøvedybde"],
    "TotalCoreRecovery": ["core recovery", "total core recovery", "kerngewinn", "recuperación"],
    "RQD": ["rqd"],
    "SPT": ["spt", "spt n", "n-spt", "nspt"],
    "Watercontent": ["water content", "moisture content", "wassergehalt", "contenido de agua", "vandindhold"],
    "Cosistency": ["consistency"],
    "UCS": ["ucs", "uniaxial compressive strength", "einaxiale druckfestigkeit"],
    "Tensile strength": ["tensile strength", "zugfestigkeit"],
    "Unitweight": ["unit weight", "wichte", "peso específico", "rumvægt"],
    "CAI": ["cai", "cerchar index", "cerchar"],
    "RMR": ["rmr"],
    "Q": ["q-value"],
    "GSI": ["gsi"],
    "FrictionAngle": ["friction angle", "reibungswinkel", "ángulo de fricción"],
    "Cohesion": ["cohesion", "kohäsion", "cohesión"],
    "Grainsize-fines": ["fines", "grain size fines", "feinkornanteil", "finos", "finkorn"],
    "LiquidLimit": ["liquid limit", "fließgrenze", "límite líquido"],
    "PlasticityLimit": ["plastic limit", "plasticity limit", "ausrollgrenze", "límite plástico"],
    "PlasticityIndex": ["plasticity index", "plastizitätszahl", "índice de plasticidad"],
    "ConsistencyIndex": ["consistency index", "konsistenzzahl", "índice de consistencia"],
    "HydraulicCoefficient": ["hydraulic conductivity", "hydraulic coefficient", "durchlässigkeit", "permeabilidad"],
    "E-Modulus": ["e-modulus", "modulus of elasticity", "e-modul", "módulo de elasticidad"],
    "PoissonsRatio": ["poisson's ratio", "poissons ratio", "poisson ratio", "querdehnzahl", "coeficiente de poisson"],
    "LayerDepthFrom": ["depth from", "from", "top depth", "von", "desde", "fra", "tiefe von"],
    "LayerDepthTo": ["depth to", "to", "bottom depth", "bis", "hasta", "til", "tiefe bis"],
}

FUZZY_LABEL_CUTOFF = 0.85
# Short labels such as "x", "y", "from" and "to" are too generic for fuzzy matching.
FUZZY_MIN_LABEL_LENGTH = 5


def normalise_label(text: str) -> str:
    """Lowercase, collapse spaces, and drop markdown emphasis and trailing colons."""
    cleaned = re.sub(r"[*_|:]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


LABEL_KEYS: dict[str, str] = {
    normalise_label(label): key
    for key, labels in FORMAT_LABELS.items()
    if key in FORMAT_TARGETS
    for label in labels
}


def resolve_label(text: str, src: str, translator) -> str | None:
    """Format key for a header or label, or None if no stage finds one.

    Stages: exact label, fuzzy label match (labels of 5+ characters only), then machine
    translation to English and an exact lookup on the English text. The translator is
    optional (None skips that stage).
    """
    label = normalise_label(text)
    if not label:
        return None
    if label in LABEL_KEYS:
        return LABEL_KEYS[label]

    if len(label) >= FUZZY_MIN_LABEL_LENGTH:
        close = difflib.get_close_matches(label, list(LABEL_KEYS), n=1, cutoff=FUZZY_LABEL_CUTOFF)
        if close:
            return LABEL_KEYS[close[0]]

    if src != "en" and translator is not None:
        english = translator.translate(label, src)
        if english and normalise_label(english) in LABEL_KEYS:
            return LABEL_KEYS[normalise_label(english)]
    return None
