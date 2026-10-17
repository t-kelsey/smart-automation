# claude_test

Experiment: turn a borehole PDF into payloads for `POST /api/boreholes`, using a
pipeline of `claude -p` calls with different models and effort levels.

## Pipeline

| # | Step | Model | Effort | Input → output |
|---|------|-------|--------|----------------|
| 1 | Filter pages | haiku | high | PDF → PDF with only real borehole log pages (classified in chunks of 10 pages) |
| 2 | Split boreholes | haiku | medium | filtered PDF → one PDF per borehole |
| 3 | Extract | sonnet | high | one borehole PDF → all data in the original wording (JSON) |
| 4 | Transform | haiku | high | extraction JSON → English, DB-shaped payload (no tools, text only) |

Step 3 also checks that the file holds exactly one borehole (`is_single_borehole`).
Step 4 targets the `boreholes` / `borehole_layers` columns from `api/priv/repo/migrations`
and the request shape in `docs/api-reference.md`; data without a column goes to `metadata`.
It then runs the API's validation rules locally (`validation_issues`). Nothing is posted to the API.

Code: `pipeline/steps/` (steps and prompts), `pipeline/local_vlm.py` (local backend), `pipeline/schemas.py` (JSON schemas),
`pipeline/claude_cli.py` (CLI wrapper, token/cost accounting), `pipeline/pdfutil.py`.

## Requirements

- [uv](https://docs.astral.sh/uv/) and the [Claude Code CLI](https://claude.com/claude-code) on `PATH`, logged in
- **poppler** (`brew install poppler`, checked at start): without `pdftoppm`, the Read tool cannot render PDF
  pages, so Claude only sees the text layer. That works for digital PDFs but not for scans,
  and colours and hatch patterns are lost.

## Usage

```sh
uv sync
uv run python -m pipeline path/to/report.pdf
# options: --out DIR (default claude_test/out)  --chunk-size 10  --workers 4
```

Progress and the final report (time, tokens, cost per step) go to stderr.

## Local model (provider `local`)

Instead of the Claude CLI, a run can use a local vision model through [Ollama](https://ollama.com) (ADR-0040);
no data leaves the machine. Set `BEM_LOCAL_URL` (see `.env.example`), pull a model and select it:

```sh
ollama pull qwen3-vl:2b        # 4 GB VRAM: use the 2b/4b sizes
uv run python -m pipeline --ai local path/to/report.pdf    # or "config": {"provider": "local"} in /execute
```

Pages are rendered to images with `pdftoppm`, the JSON schema is sent as Ollama's `format`. Context is small, so
step 1 classifies 2 pages per call and steps 2/3 take at most `BEM_LOCAL_MAX_PAGES` pages (step 2 fails above that,
step 3 reads only the first pages and adds a warning). Expect weaker colour/hatch reading than with Claude.
`/execute` answers `422` for `provider: "local"` when `BEM_LOCAL_URL` is unset.

## HTTP server (`POST /execute`)

The API sends uploaded documents here (`PIPELINE_URL=http://localhost:8000/execute`, ADR-0033).

```sh
uv run python -m pipeline.server   # settings from bem/.env (copy .env.example), port BEM_PORT, default 8000
```

- `POST /execute`: JSON body with the document id, the API's `pipeline_runs.id` (as `pipeline_id`) and the run config.
  It answers `202` at once and queues the run; invalid input returns `422`. The document must already exist in the API.
  ```json
  {"document_id": "<uuid>", "pipeline_id": "<pipeline_runs.id>, echoed back",
   "config": {"filter": {"model": "haiku", "effort": "high"}, "split": {...}, "extract": {...}, "transform": {...}}}
  ```
  `config` is optional and so is every step in it; omitted steps use their defaults ([config.py](pipeline/config.py)).
  One worker starts stage 1 (filter) by downloading the PDF with `GET /api/documents/:id/file` (a document that is
  missing or not a PDF ends `failed`), runs the pipeline and posts each borehole to `POST /api/boreholes` (linked to the
  document). It finishes with `PUT /api/pipeline_runs/:id/status` set to `completed` or `failed` (ADR-0035) — not a
  document status, `pipeline_runs` is the source of truth for a run's outcome.

```sh
curl -X POST http://localhost:8000/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "pipeline_id": "my-pipeline",
    "config": {
      "filter":    {"model": "haiku",  "effort": "high"},
      "split":     {"model": "haiku",  "effort": "medium"},
      "extract":   {"model": "sonnet", "effort": "high"},
      "transform": {"model": "haiku",  "effort": "high"}
    }
  }'
# -> 202 {"document_id": "...", "pipeline_id": "my-pipeline", "status": "queued", "config": {...}}
```

- After every step the server uploads its output: `POST /api/exec_stages` (`type` filter|split|extract|transform, `position` = 1-based
  borehole index for extract/transform, `data` = the step's JSON), then `POST /api/reports` (`{"steps": [...]}`) and
  `POST /api/boreholes` per borehole. Boreholes must satisfy DIN 4023 ([din4023.py](pipeline/din4023.py), checked against
  `standards/din-4023/din-4023.json`): petrography is normalised to the standard's terms and a borehole with an unmappable
  layer is not uploaded (the document ends `failed`). Client: [api_service.py](pipeline/api_service.py), URL from `BEM_API_URL`
  (`.env`, default `http://localhost:4000`).
- `BEM_ENV=dev` (default) also writes results, report and debug files under `out/`; `BEM_ENV=prod` writes nothing locally
  (intermediate PDFs go to a temp dir that is deleted, as is the uploaded file).
- Tests: `uv run python -m unittest discover tests`.
- `GET /health`: `{"status": "ok", "queued": n}`.
- Env: `BEM_API_URL`, `BEM_PORT`, `BEM_WORKDIR` (default `out/server`), `BEM_CHUNK_SIZE`, `BEM_WORKERS`, `BEM_AI`.
- The queue is in memory: a restart loses queued files.

## Output

Everything is written to `out/<pdf-name>/` (git-ignored). Every file name is prefixed with
the run id (`YYYYMMDD-HHMMSS_`, the start time of the execution), the same for all files of one
run, e.g. `20261017-173012_borehole_01.json`. The run id is printed at start:

```
01_filter/   classification.json, borehole_pages.pdf, chunks/
02_split/    grouping.json, borehole_NN.pdf
03_extract/  borehole_NN.json     raw extraction
04_transform/ borehole_NN.json    {payload, validation_issues}
report.json  per-step time, tokens, cost
result.json  final payloads for all boreholes
```

Time per step is wall clock; calls inside a step run in parallel (`--workers`).
Cost is what the CLI reports, so it includes Claude Code's own system prompt
(roughly 40k cached tokens per call), which dominates small inputs.

## Data confidentiality

Every PDF page is sent to Claude. Do not run this on the confidential files in
`../data/` (see the root `CLAUDE.md`). `out/` contains copies of the input pages
and is git-ignored; delete it when done.

## Known limitations

- Step 4 uses a small model for translation and the unit/coordinate conversions
  (e.g. Gauss-Krüger to EPSG); check `validation_issues` and the metadata notes.
- Step 2 reads the whole filtered PDF in one call; very long ones need many Read calls.
- The API requires `elevation_m >= 0`, so boreholes below sea level fail validation.
