"""JSON schemas passed to `claude --json-schema` for each step."""


def _t(type_: str) -> dict:
    """Nullable scalar: the prompts ask for null when a value is missing."""
    return {"type": [type_, "null"]}


# Step 1: per-page classification of a chunk of the PDF
CLASSIFY_PAGES = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "1-based page number in this file"},
                    "is_borehole_log": {"type": "boolean"},
                    "reason": {"type": "string", "description": "max 12 words"},
                },
                "required": ["page", "is_borehole_log", "reason"],
            },
        }
    },
    "required": ["pages"],
}

# Step 2: grouping of the kept pages into boreholes
SPLIT_BOREHOLES = {
    "type": "object",
    "properties": {
        "boreholes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "borehole name/id as written, or a short description"},
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "1-based page numbers in this file, ascending",
                    },
                },
                "required": ["label", "pages"],
            },
        }
    },
    "required": ["boreholes"],
}

# Step 3: everything on one borehole log, in the document's own wording
EXTRACT_BOREHOLE = {
    "type": "object",
    "properties": {
        "is_single_borehole": {
            "type": "boolean",
            "description": "false if the file contains zero or more than one borehole",
        },
        "borehole_count_in_file": {"type": "integer"},
        "source_language": _t("string"),
        "name": _t("string"),
        "external_id": _t("string"),
        "project": _t("string"),
        "client": _t("string"),
        "place": _t("string"),
        "purpose": _t("string"),
        "drilling_method": _t("string"),
        "date_started": _t("string"),
        "date_ended": _t("string"),
        "coordinates": {
            "type": "object",
            "properties": {
                "x": _t("number"),
                "y": _t("number"),
                "coordinate_system_as_written": _t("string"),
                "raw_text": _t("string"),
            },
            "required": ["x", "y", "coordinate_system_as_written", "raw_text"],
        },
        "elevation_m": _t("number"),
        "total_depth_m": _t("number"),
        "borehole_length_m": _t("number"),
        "groundwater_level_m": _t("number"),
        "layers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "depth_from_m": {"type": "number"},
                    "depth_to_m": {"type": "number"},
                    "description": {"type": "string", "description": "full layer text, original wording"},
                    "stratigraphy": _t("string"),
                    "petrography": _t("string"),
                    "color": _t("string"),
                    "notes": _t("string"),
                },
                "required": [
                    "depth_from_m",
                    "depth_to_m",
                    "description",
                    "stratigraphy",
                    "petrography",
                    "color",
                    "notes",
                ],
            },
        },
        "other_information": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                "required": ["label", "value"],
            },
            "description": "any other header/legend/remark data that fits no field above",
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "illegible parts, ambiguities, inconsistencies",
        },
    },
    "required": [
        "is_single_borehole",
        "borehole_count_in_file",
        "source_language",
        "name",
        "external_id",
        "project",
        "client",
        "place",
        "purpose",
        "drilling_method",
        "date_started",
        "date_ended",
        "coordinates",
        "elevation_m",
        "total_depth_m",
        "borehole_length_m",
        "groundwater_level_m",
        "layers",
        "other_information",
        "warnings",
    ],
}

# Step 4: payload for POST /api/boreholes (api/priv/repo/migrations, docs/api-reference.md)
DB_PAYLOAD = {
    "type": "object",
    "properties": {
        "borehole": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "external_id": _t("string"),
                "purpose": _t("string"),
                "place": _t("string"),
                "client": _t("string"),
                "drilling_method": _t("string"),
                "drilled_at": {**_t("string"), "description": "ISO date YYYY-MM-DD"},
                "end_date": {**_t("string"), "description": "ISO date YYYY-MM-DD"},
                "x": _t("number"),
                "y": _t("number"),
                "epsg": _t("integer"),
                "source_coordinate_system": _t("string"),
                "source_coordinate_raw": _t("string"),
                "total_depth_m": _t("number"),
                "borehole_length_m": _t("number"),
                "elevation_m": _t("number"),
                "groundwater_level_m": _t("number"),
                "metadata": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": [
                "name",
                "external_id",
                "purpose",
                "place",
                "client",
                "drilling_method",
                "drilled_at",
                "end_date",
                "x",
                "y",
                "epsg",
                "source_coordinate_system",
                "source_coordinate_raw",
                "total_depth_m",
                "borehole_length_m",
                "elevation_m",
                "groundwater_level_m",
                "metadata",
            ],
        },
        "layers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"},
                    "depth_from_m": {"type": "number"},
                    "depth_to_m": {"type": "number"},
                    "stratigraphy": _t("string"),
                    "petrography": _t("string"),
                    "color": _t("string"),
                    "raw_text": _t("string"),
                    "metadata": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": [
                    "position",
                    "depth_from_m",
                    "depth_to_m",
                    "stratigraphy",
                    "petrography",
                    "color",
                    "raw_text",
                    "metadata",
                ],
            },
        },
    },
    "required": ["borehole", "layers"],
}

# Step 4 fallback: best-effort EPSG guess when coordinate_systems.resolve_epsg found nothing.
GUESS_EPSG = {
    "type": "object",
    "properties": {
        "epsg": _t("integer"),
        "reasoning": _t("string"),
    },
    "required": ["epsg", "reasoning"],
}
