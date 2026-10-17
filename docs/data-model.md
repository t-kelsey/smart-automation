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

## Pipeline stage tracking (implemented, ADR-0030)

See "Pipeline Stage Tracking" in [elixir-backend-borehole-pipeline.md](elixir-backend-borehole-pipeline.md). Latest-run-only: a rerun upserts `pipeline_stage_runs`/`triage_sections` or cascades deletes down to `extraction_results`/`sink_results`.

```mermaid
erDiagram
    DOCUMENTS ||--o{ PIPELINE_STAGE_RUNS : document_id
    DOCUMENTS ||--o{ TRIAGE_SECTIONS : document_id
    TRIAGE_SECTIONS ||--o| EXTRACTION_RESULTS : triage_section_id
    EXTRACTION_RESULTS ||--o| SINK_RESULTS : extraction_result_id
    BOREHOLES ||--o| SINK_RESULTS : created_borehole_id

    PIPELINE_STAGE_RUNS {
        binary_id id PK
        binary_id document_id FK "not unique alone"
        string stage UK "ocr | translation - UK is (document_id, stage)"
        string status "ok | error"
        jsonb output
        string error
        utc_datetime started_at
        utc_datetime finished_at
    }

    TRIAGE_SECTIONS {
        binary_id id PK
        binary_id document_id FK "not unique alone"
        integer section_index UK "UK is (document_id, section_index)"
        string borehole_id_guess
        string raw_markdown
        jsonb translate_errors
    }

    EXTRACTION_RESULTS {
        binary_id id PK
        binary_id triage_section_id FK
        string status "ok | error"
        jsonb extracted_fields
        jsonb validation_issues
        string error
    }

    SINK_RESULTS {
        binary_id id PK
        binary_id extraction_result_id FK
        string target "api | json | print"
        boolean success
        integer response_status
        binary_id created_borehole_id FK
        string error
    }
```
