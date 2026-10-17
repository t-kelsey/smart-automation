# Data Model

Entity-relationship diagram of the tables described in [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md). Mermaid renders this directly in GitHub and VS Code's markdown preview, so it stays diffable as the schema evolves.

## Implemented

```mermaid
erDiagram
    DOCUMENTS ||--o{ BOREHOLE_DOCUMENTS : document_id
    BOREHOLES ||--o{ BOREHOLE_DOCUMENTS : borehole_id
    BOREHOLES ||--o{ BOREHOLE_LAYERS : borehole_id

    DOCUMENTS {
        binary_id id PK
        string original_filename
        string storage_path "never exposed publicly"
        string mime_type
        string source_country
        string status "pending/processing/extracted/failed/reviewed"
        integer page_count
        integer size_bytes
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
    }
```

## Pipeline runs & stage tracking (implemented, ADR-0034/ADR-0035)

See "Pipeline Runs & Stage Tracking" in [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md) and [ADR-0037](adr/0037-end-to-end-document-pipeline-run-boreholes-flow.md) for the full flow. `exec_stages` is append-only (reruns add rows, not upserts); `pipeline_runs` tracks one submission/polling lifecycle per document.

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
        jsonb data "the step's JSON file as-is"
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
        string status "new | running | completed | failed"
        jsonb config "per-stage model/effort choices, as-is"
    }
```
