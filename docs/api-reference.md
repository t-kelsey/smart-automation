# API Reference: Boreholes (Map/Search API)

Base URL: `http://localhost:4000/api` (dev). All responses are JSON (`Content-Type: application/json`). No authentication is currently implemented.

This covers the endpoints implemented so far — Task 4 ("Map/Search API") from [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md). Ingestion/upload endpoints (Task 2) don't exist yet.

> **Confidentiality**: `documents.storage_path` and `documents.raw_extraction` are never returned by any endpoint (see ADR-0014). Only `id`, `original_filename`, `mime_type`, `source_country`, `status` are exposed for a document.

---

## `GET /api/boreholes`

List boreholes as a GeoJSON `FeatureCollection`, optionally filtered to a bounding box. This is the endpoint the map view uses to render markers for the current viewport.

### Query parameters

| Param | Required | Format | Description |
|---|---|---|---|
| `bbox` | no | `minLon,minLat,maxLon,maxLat` (4 comma-separated floats) | Only return boreholes whose `location` intersects this envelope. Omit to get every borehole. |

### Response `200 OK`

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [9.177, 48.776] },
      "properties": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "B 1/59 Schönberg",
        "external_id": "BH_AB01",
        "purpose": "Hydrogeologische Untersuchung",
        "drilling_method": "Rotary core drilling",
        "drilled_at": "1959-06-12",
        "end_date": null,
        "source_coordinate_system": "32U UTM",
        "source_coordinate_raw": "412559.379, 5315392.271",
        "total_depth_m": "18.3",
        "borehole_length_m": null,
        "elevation_m": "262.0",
        "groundwater_level_m": null,
        "verified": false,
        "metadata": {},
        "inserted_at": "2026-10-17T09:06:00Z",
        "updated_at": "2026-10-17T09:06:00Z"
      }
    }
  ]
}
```

`geometry` is `null` if the borehole has no `location` set yet (e.g. not yet georeferenced).

Each item in `properties` is every `boreholes` column except `location` (promoted to `geometry`), `borehole_layers`, and `documents` (omitted entirely from the list endpoint — fetch a single borehole's detail for those).

### Response `400 Bad Request`

Returned if `bbox` is present but malformed (wrong number of parts, or a part isn't a valid float):

```json
{ "errors": { "detail": "invalid bbox, expected minLon,minLat,maxLon,maxLat" } }
```

### Example

```bash
curl "http://localhost:4000/api/boreholes?bbox=9.0,48.0,10.0,49.0"
```

---

## `GET /api/boreholes/:id`

Full detail for a single borehole: Stammdaten + ordered stratigraphy layers + associated (confidentiality-filtered) documents. This is what the borehole detail panel/page uses.

### Path parameters

| Param | Format | Description |
|---|---|---|
| `id` | UUID | The borehole's `id`. |

### Response `200 OK`

```json
{
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "B 1/59 Schönberg",
    "external_id": "BH_AB01",
    "purpose": "Hydrogeologische Untersuchung",
    "drilling_method": "Rotary core drilling",
    "drilled_at": "1959-06-12",
    "end_date": null,
    "source_coordinate_system": "32U UTM",
    "source_coordinate_raw": "412559.379, 5315392.271",
    "total_depth_m": "18.3",
    "borehole_length_m": null,
    "elevation_m": "262.0",
    "groundwater_level_m": null,
    "verified": false,
    "metadata": {},
    "inserted_at": "2026-10-17T09:06:00Z",
    "updated_at": "2026-10-17T09:06:00Z",
    "location": { "type": "Point", "coordinates": [9.177, 48.776] },
    "layers": [
      {
        "id": "b3f1...",
        "position": 1,
        "depth_from_m": "0.0",
        "depth_to_m": "3.5",
        "stratigraphy": "Neuenburg-Formation",
        "petrography": "Kies [gerundet] (steinig, schwach grobsandig)",
        "color": "grau",
        "raw_text": "0,0-3,5 Kies...",
        "metadata": {}
      }
    ],
    "documents": [
      {
        "id": "c7a2...",
        "original_filename": "B1-59_Schichtenverzeichnis.pdf",
        "mime_type": "application/pdf",
        "source_country": null,
        "status": "pending"
      }
    ]
  }
}
```

`layers` is always ordered by `position` ascending. `documents` reflects the many-to-many `documents` ↔ `boreholes` relationship (see ADR-0012) — zero, one, or many entries.

### Response `404 Not Found`

Returned if no borehole with that `id` exists (standard Phoenix error shape via `ApiWeb.ErrorJSON`):

```json
{ "errors": { "detail": "Not Found" } }
```

### Example

```bash
curl "http://localhost:4000/api/boreholes/3fa85f64-5717-4562-b3fc-2c963f66afa6"
```

---

## `GET /api/boreholes/search`

Free-text search across borehole name, external ID, and stratigraphy of any of its layers. Returns the same GeoJSON `FeatureCollection` shape as `GET /api/boreholes` (not the detail shape) — intended to feed search results straight back onto the map.

### Query parameters

| Param | Required | Description |
|---|---|---|
| `q` | no (defaults to empty string, matching everything) | Case-insensitive substring match against `name`, `external_id`, or any layer's `stratigraphy`. |

A borehole matching through more than one of its layers (e.g. two layers with the same `stratigraphy`) is still only returned once.

### Response `200 OK`

Same shape as [`GET /api/boreholes`](#get-apiboreholes).

### Example

```bash
curl "http://localhost:4000/api/boreholes/search?q=sch%C3%B6nberg"
```

---

## Route ordering note

`/api/boreholes/search` is registered before `/api/boreholes/:id` in the router — required so Phoenix doesn't match the literal path segment `"search"` as an `:id`.
