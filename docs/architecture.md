# Architecture

Snapshot of the current system (code state of 2026-10-17). Decisions behind it are in [`adr/`](adr/), the endpoints in [`api-reference.md`](api-reference.md).

## Components

```mermaid
flowchart LR
    user([User / Browser])

    subgraph web["web (SvelteKit 3 / Svelte 5, :3000)"]
        ui["Routes + components<br/>/upload, /pipeline, /borehole/:id, /map, /search"]
        svc["Services<br/>Borehole / Search / Upload / Pipeline"]
        repo["API repositories<br/>(ADR-0009, ADR-0029)"]
        proxy["hooks.server.ts<br/>forwards /api/* to the API"]
        ui --> svc --> repo --> proxy
    end

    subgraph api["api (Phoenix 1.8 JSON API, :4000)"]
        router["Router /api<br/>boreholes, documents,<br/>pipeline_runs, exec_stages, reports"]
        ctx["Api.Boreholes (Ecto context)<br/>Api.Pipeline (Req webhook client)"]
        router --> ctx
    end

    subgraph bem["bem pipeline (Python / FastAPI, :8000)"]
        exec["POST /execute<br/>job queue + worker thread"]
        steps["1 filter → 2 split → 3 extract → 4 transform<br/>DIN 4023 conformance"]
        exec --> steps
    end

    db[("PostgreSQL + PostGIS<br/>boreholes, borehole_layers, documents,<br/>pipeline_runs, exec_stages, reports")]
    fs[("Document storage<br/>volume /data/storage<br/>(confidential PDFs)")]
    claude{{"claude CLI<br/>(Claude models, OCR + LLM)"}}

    user <--> ui
    proxy <-->|"HTTP/JSON, multipart"| router
    ctx <--> db
    ctx <--> fs
    ctx -->|"POST /execute<br/>{document_id, pipeline_id, config}"| exec
    steps -->|"GET /documents/:id/file<br/>POST /documents, /exec_stages, /reports, /boreholes<br/>PUT /pipeline_runs/:id/status"| router
    steps <--> claude
```

All four services run via `docker-compose.yml` (`db`, `api`, `web`, `pipeline`). The web app talks only to the API (ADR-0029); the pipeline never touches the database or storage directly, it only uses the API.

## Flow 1: Upload a document and start a parsing pipeline

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant W as Web (/upload, /upload/config)
    participant A as API (Phoenix)
    participant S as Storage + DB
    participant P as bem pipeline
    participant C as claude CLI

    U->>W: Choose files (pdf, png, jpg, tif, docx)
    Note over W: Files are only queued in the browser<br/>(upload-queue), nothing is stored yet (ADR-0038)
    U->>W: Configure model + effort per step, "Start extraction"
    W->>A: POST /api/documents (multipart file)
    A->>S: Store file, insert documents row
    A-->>W: 201 {id, original_filename, status}
    W->>A: POST /api/pipeline_runs {document_id, config}
    A->>S: Insert pipeline_runs (status new)
    A->>P: POST /execute {document_id, pipeline_id, config}
    P-->>A: 202 queued
    A->>S: pipeline_runs.status = running
    A-->>W: 201 pipeline run
    W->>W: Open /pipeline/:id, poll every 3 s

    Note over P: Worker thread takes the job
    P->>A: GET /api/documents/:id/file
    A-->>P: PDF bytes (scratch copy, deleted afterwards)
    loop Stages filter, split, extract, transform
        P->>C: Pages / text + prompt
        C-->>P: Structured result
        P->>A: POST /api/exec_stages {type, run_id, data, document_ids, position}
    end
    P->>A: POST /api/documents (split-out PDF per borehole)
    P->>A: POST /api/reports (model, time, tokens, cost per step)
    loop Each borehole
        P->>P: Validate against DIN 4023
        P->>A: POST /api/boreholes {borehole, layers, document_id, additional_document_ids}
        A->>S: Insert borehole, layers, document links
    end
    P->>A: PUT /api/pipeline_runs/:id/status (completed | failed)

    W->>A: GET /api/pipeline_runs/:id (poll)
    A-->>W: run + exec_stages + report
    W-->>U: Stage and job progress
```

Notes:

- The webhook call carries no file bytes; the pipeline pulls the file by `document_id` (ADR-0033).
- Without `PIPELINE_URL` the run stays `new` and nothing is processed. If the pipeline cannot be reached the run is `failed`.
- Only the stage results of a run whose `run_id` equals the `pipeline_runs.id` show up in the UI (ADR-0039).

## Flow 2: View a borehole in the UI

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant W as Web (SvelteKit)
    participant A as API (Phoenix)
    participant D as PostgreSQL / PostGIS
    participant S as Document storage

    U->>W: Open /search, /map or /borehole
    W->>A: GET /api/boreholes/search | GET /api/boreholes (paged, filtered)
    A->>D: Query (PostGIS for coordinates)
    D-->>A: Rows
    A-->>W: JSON list
    W-->>U: Table / MapLibre map with markers

    U->>W: Select a borehole, /borehole/:id
    Note over W: +layout.ts load() → createServices() → BoreholeService
    W->>A: GET /api/boreholes/:id
    A->>D: Borehole + layers + linked documents
    D-->>A: Data
    A-->>W: JSON (core data, layers, documents)
    W->>W: Mapper to domain model, DIN 4023 colours and patterns
    W-->>U: Cross section, core data, layers table, documents

    U->>W: Open a document (/document/:id) or download it
    W->>A: GET /api/documents/:id/file
    A->>S: Stream file
    S-->>A: Bytes
    A-->>W: PDF / image
    W-->>U: Source document viewer next to the borehole
```

Notes:

- UI → service → repository → API (ADR-0009). UI code does not import repositories (ESLint enforces it).
- In `pnpm dev` the Vite proxy forwards `/api`; in Docker `hooks.server.ts` forwards it to `API_INTERNAL_URL`.
- Editing and review pages (`/borehole/:id/edit`, `/review`) exist, but saving changes is not wired to the API yet.
