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

Code: `pipeline/steps.py` (steps and prompts), `pipeline/schemas.py` (JSON schemas),
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
