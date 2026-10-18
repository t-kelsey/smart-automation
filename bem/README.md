# bem

Extraction pipeline: turns a borehole report (PDF) into standardised boreholes in the geodatabase.

## Why it exists

Borehole logs are unstructured, multilingual, differ by company and decade and carry meaning in colour and hatch patterns. Classic OCR plus rules does not cope with that variety. This component uses vision-capable LLMs to read the pages and brings the result into one standard: English, the DIN 4023 terms, WGS84-ready coordinates and the API's data model. It runs as an HTTP service that the API calls when a user starts a run.

## Pipeline

Default pipeline steps and configurations:

| #   | Step            | Model  | Effort | Input → output                                                     |
| --- | --------------- | ------ | ------ | ------------------------------------------------------------------ |
| 1   | Filter pages    | haiku  | high   | PDF → PDF with only real borehole log pages (chunks of 10 pages)   |
| 2   | Split boreholes | haiku  | medium | filtered PDF → one PDF per borehole                                |
| 3   | Extract         | sonnet | high   | one borehole PDF → all data in the original wording (JSON)         |
| 4   | Transform       | haiku  | high   | extraction JSON → English, DB-shaped payload, DIN 4023 petrography |

Models and effort are configurable per run (defaults in [config.py](pipeline/config.py)). Step 3 also checks that the file holds exactly one borehole. A borehole with a layer that cannot be mapped to DIN 4023 is not uploaded and its stage ends `failed`. Every stage is tracked in the API (status, model, tokens, cost) and the run ends `completed`, `failed` or `stopped`. A failed or stopped extract/transform job can be redone on its own as a new stage of the same run (`POST /runs/{pipeline_id}/retry`, see below).

## Development setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Python ≥ 3.12, **poppler** (`brew install poppler`; without `pdftoppm` scans, colours and hatching are lost) and an AI backend: an [OpenRouter](https://openrouter.ai) API key (default, see [AI backends](#ai-backends)), or for development only the [Claude Code CLI](https://claude.com/claude-code) on `PATH`, logged in (`BEM_AI=claude_cli`).

```bash
cd bem
cp .env.example .env                         # BEM_API_URL=http://localhost:4000 etc.
uv sync
uv run python -m pipeline.server             # HTTP service on :8000 (POST /execute)

# Optional commands
uv run python -m pipeline path/to/report.pdf # one-off run, results under out/
uv run python -m unittest discover tests     # tests
```

Service endpoints:

- `POST /execute` — `{document_id, pipeline_id, config?}`; answers `202` and queues the run. The worker downloads the PDF from the API, runs the stages and posts the boreholes to `POST /api/boreholes`.
- `POST /runs/{pipeline_id}/retry` — `{document_id, stage: extract|transform, position, config?}`; answers `202` and queues the redo of one failed or stopped borehole job of a finished run as a new stage (extract continues with transform). It reads the run's earlier results from the API; the run ends `completed` only if every borehole's newest extract/transform succeeded (ADR-0044). `409` while the run is queued or running.
- `POST /runs/{pipeline_id}/stop` — cancels a queued or running run.
- `GET /health` — queue length and active runs.

`BEM_ENV=dev` also writes results, a report and debug files under `out/` (gitignored); `prod` keeps nothing on disk. The queue is in memory, so a restart loses queued runs. Settings: `BEM_API_URL`, `BEM_PORT`, `BEM_WORKERS`, `BEM_CHUNK_SIZE`, `BEM_AI`, `BEM_WORKDIR`, and for OpenRouter `OPENROUTER_API_KEY`, `BEM_OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`.

### AI backends

**OpenRouter is the default backend.** The `claude` CLI backend (`BEM_AI=claude_cli`) is meant for development only: it needs a logged-in CLI or Anthropic credentials, which is awkward to ship in a deployment.

#### OpenRouter (default, prototype)

> **Prototype.** The OpenRouter backend shows that the pipeline is not tied to one provider: the stages only talk to the `AI` interface, and a second backend plugged in without changing them. The architecture is modular an ai-provider agnostic. After the hackathon it can be further developed and enhanced for a real product.

Set `OPENROUTER_API_KEY=...` in `.env` (`BEM_AI=openrouter` is the default; the `claude` CLI is not needed, `pdftoppm` still is; in Docker compose set the same variables in the root `.env`). Pages are rendered to images and sent with the prompt; the answer is requested as JSON matching the step's schema, and if a provider rejects the schema (e.g. too many nullable fields) the backend falls back to plain JSON mode, which is not schema-validated by the provider. The default step models `haiku`/`sonnet`/`opus` map to `anthropic/claude-*-4.5`; a per-run model containing a `/` (e.g. `google/gemini-2.5-flash`) is used as is, and `BEM_OPENROUTER_MODEL` forces one model for all steps. Effort is sent as OpenRouter's `reasoning.effort` (`xhigh`/`max` → `high`). Cost comes from OpenRouter's usage report.

## Technology

| Choice                                                 | Why                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Python**                                             | Best ecosystem for PDF handling and AI tooling; the work is I/O bound, so it needs no heavy framework.                                                                                                                                                                                                                                                   |
| **OpenRouter (default), `claude` CLI for development** | Vision models read page images directly (scans, colours, hatching) and return JSON. A small model (haiku) does cheap classification and splitting, a stronger one (sonnet) does the extraction. The `AI` base class in [ai.py](pipeline/ai.py) has two backends: [OpenRouter](pipeline/openrouter.py) (default) and the `claude` CLI (development only). |
| **Four small stages**                                  | Each stage is cheap to retry, measurable (tokens, cost) and uses the right model for its job.                                                                                                                                                                                                                                                            |
| **pypdf, poppler**                                     | Split and filter PDFs; render pages to images for the model.                                                                                                                                                                                                                                                                                             |
| **FastAPI + uvicorn**                                  | A small async HTTP surface (`/execute`, `/health`) with request validation.                                                                                                                                                                                                                                                                              |
| **httpx**                                              | Client for the API ([api_service.py](pipeline/api_service.py)).                                                                                                                                                                                                                                                                                          |
| **uv**                                                 | Fast, reproducible installs from `uv.lock`.                                                                                                                                                                                                                                                                                                              |

## Data confidentiality and limitations

Every page of a processed PDF is sent to the selected AI model (by default via OpenRouter). Do not run the pipeline on confidential files, including `../data/`. Also:

- PDFs, images (PNG, JPEG, TIFF) and Word `.docx` files are processed (Word needs LibreOffice, `soffice`, which the Docker image includes; locally e.g. `brew install --cask libreoffice`).
- The transform step uses a small model for translation and unit and coordinate conversion; check `validation_issues` and the metadata notes.
- There is no accuracy evaluation against ground truth yet.
- The OpenRouter backend is a prototype. Ideas for extending it:
  - compare models and providers per stage against a ground-truth set and pick defaults from the results (cheaper models for filter and split, stronger ones for extract);
  - validate every answer against the step's JSON schema ourselves, because the plain-JSON fallback is not validated by the provider;
  - tune page rendering (resolution, page count per call) and add more backends behind the same `AI` interface, including self-hosted models for confidential data;
  - add streaming and rate-limit handling, and track cost budgets per run.
