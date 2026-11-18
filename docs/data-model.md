# Data Model

Entity-relationship diagram of the tables described in [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md). Mermaid renders this directly in GitHub and VS Code's markdown preview, so it stays diffable as the schema evolves.

## Implemented

```mermaid
erDiagram
    DOCUMENTS ||--o{ BOREHOLE_DOCUMENTS : document_id
    BOREHOLES ||--o{ BOREHOLE_DOCUMENTS : borehole_id
    BOREHOLES ||--o{ BOREHOLE_LAYERS : borehole_id
    BOREHOLES ||--o{ FIELD_FLAGS : borehole_id
    BOREHOLE_LAYERS ||--o{ FIELD_FLAGS : layer_id
    BOREHOLES ||--o{ FIELD_EDITS : borehole_id

    DOCUMENTS {
        binary_id id PK
        string original_filename
        string storage_path "never exposed publicly"
        string mime_type
        string source_country
        string status "pending/processing/extracted/failed/reviewed"
        integer page_count
        integer size_bytes
        string sha256 "hex SHA-256 of the upload, indexed, null for old rows"
        jsonb raw_extraction "never exposed publicly"
    }

    BOREHOLES {
        binary_id id PK
        string name
        string external_id "not unique"
        string purpose
        string place
        string client
        string drilling_method
        date drilled_at
        date end_date
        geometry location "Point, 4326"
        string source_coordinate_system
        string source_coordinate_raw
        decimal total_depth_m
        decimal borehole_length_m
        decimal elevation_m
        decimal groundwater_level_m
        boolean verified
        utc_datetime verified_at "set with verified (ADR-0006)"
        jsonb sources "field to {document_id, page, box} (ADR-0006)"
        float source_x "x as written in the document, source CRS"
        float source_y "y as written in the document, source CRS"
        integer source_epsg "EPSG of source_x/source_y; all three set with location"
        jsonb metadata
    }

    BOREHOLE_DOCUMENTS {
        binary_id id PK
        binary_id borehole_id FK
        binary_id document_id FK
        string role "original | additional - at most one original per borehole"
    }

    BOREHOLE_LAYERS {
        binary_id id PK
        binary_id borehole_id FK "on delete: cascade"
        integer position
        decimal depth_from_m
        decimal depth_to_m
        string stratigraphy
        string petrography
        string color
        string raw_text
        jsonb metadata
        jsonb source "{document_id, page, box} of the row, nullable (ADR-0006)"
        jsonb sources "layer field to {document_id, page, box} (ADR-0006)"
    }

    FIELD_FLAGS {
        binary_id id PK
        binary_id borehole_id FK "on delete: cascade"
        binary_id layer_id "nullable, NO foreign key: flags of a deleted layer are hidden until it is restored"
        string field "column name, location, layer"
        string severity "warning | error"
        text message
        string origin "rule | validator"
        string code "rule id, null for validator flags"
        jsonb suggestion "nullable, any JSON: proposed value"
        utc_datetime_usec resolved_at "null = open"
        string resolved_by "human | rule"
    }

    FIELD_EDITS {
        binary_id id PK
        binary_id borehole_id FK "on delete: cascade"
        binary_id layer_id "nullable, NO foreign key: history survives a deleted layer"
        string field
        jsonb old_value "any JSON"
        jsonb new_value "any JSON"
        string source "validator | human"
        text reason
        utc_datetime_usec inserted_at "append-only, no updated_at"
    }
```

`field_flags` and `field_edits` (ADR-0006): flags are open until `resolved_at` is set (`field_flags.layer_id` has no foreign key like `field_edits.layer_id`: flags of a deleted layer stay in the table but are left out of `flags`, `open_flag_count`, sorting and filtering until the layer is restored with its old id); `exec_stages` timestamps have microsecond precision, so the newest row per `(type, position)` is unambiguous; edits are the append-only history of validator corrections and human edits. `old_value`/`new_value` are stored as `jsonb` through `Api.Boreholes.JsonValue` (a number, string, object or `NULL`). `location` values are `{"x", "y", "epsg"}`, `layer` values a snapshot of the layer. Layer `position` is always the rank by `depth_from_m`. The rules are in the [API reference](api-reference.md#plausibility-checks).

## Pipeline runs & stage tracking (implemented, ADR-0002)

See "Pipeline Runs & Stage Tracking" in [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md) and [ADR-0002](adr/0002-document-intake-and-pipeline-runs.md) for the full flow. `exec_stages` keeps every attempt (reruns add rows, not upserts) and follows each stage through `new → running → success | failed | stopped` (ADR-0002); `pipeline_runs` tracks one submission/polling lifecycle per document and can be stopped.

```mermaid
erDiagram
    DOCUMENTS ||--o{ STAGE_DOCUMENT_LINKS : document_id
    EXEC_STAGES ||--o{ STAGE_DOCUMENT_LINKS : exec_stage_id
    DOCUMENTS ||--o{ REPORTS : document_id
    DOCUMENTS ||--o{ PIPELINE_RUNS : document_id

    EXEC_STAGES {
        binary_id id PK
        string type "filter | split | extract | transform"
        string run_id "groups every stage + the report of one run"
        integer position "borehole index within the run; null for filter/split"
        string status "new | running | success | failed | stopped"
        jsonb data "the step's JSON result as-is; null until it has one"
        text error "why it failed or stopped"
        string model
        string effort
        jsonb usage "calls, tokens, cost_usd, ... of this stage or borehole"
        utc_datetime_usec started_at "stamped on running"
        utc_datetime_usec finished_at "stamped on success | failed | stopped"
    }

    STAGE_DOCUMENT_LINKS {
        binary_id id PK
        binary_id exec_stage_id FK
        binary_id document_id FK
    }

    REPORTS {
        binary_id id PK
        binary_id document_id FK
        string run_id
        jsonb data "report.json: per-step model/time/token/cost stats"
    }

    PIPELINE_RUNS {
        binary_id id PK
        binary_id document_id FK
        string status "new | running | completed | failed | stopped"
        jsonb config "per-stage model/effort choices, as-is"
        string current_stage "type of the stage that last started"
        text error "why the run failed or was stopped"
        utc_datetime_usec started_at
        utc_datetime_usec finished_at
    }
```
