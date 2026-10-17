# bem – borehole extraction pipeline

Pipeline (ADR-0001, ADR-0007): **OCR → translation → triage → extraction (Qwen) → output**.
`src/bem/main.py` runs all stages on any number of files or folders; each stage can also be run
alone (sections 1-3 below).

```
report.pdf ─ocr─▶ markdown ─translate─▶ markdown ─triage─▶ one Borehole per ID ─qwen─▶ Borehole ─▶ api | json | print
```

Triage splits a report into one section per borehole ID, and extraction runs once per section.
With `--debug`, every stage writes its result under `output/` (gitignored, it holds confidential text):

```
output/ocr/<folder>__<file>.md   output/translate/<folder>__<file>.md
output/triage/<folder>__<file>__<n>.json   output/extraction/<folder>__<file>__<n>.json
```

Once the pipeline works end to end, see [`API_INTEGRATION.md`](API_INTEGRATION.md) for how to
report stage results and the final boreholes to `api/`.

All commands run from this folder (`bem/`) with [uv](https://docs.astral.sh/uv/). The first
`uv run` creates `.venv` and installs the dependencies from `uv.lock` (Python 3.14 is required;
uv downloads it if missing).

```bash
cd bem
uv sync
```

## Run the full pipeline

`uv run bem` calls `bem.main:main` (entry point in `pyproject.toml`). `python -m bem.main` does the same.
It needs the model server from section 3 and the translation models from section 2.

```bash
uv run bem <file-or-dir>... [--to print|json|api] [--out-dir DIR] [--api-url URL] [--debug]

uv run bem ../data/BoreholeData/<folder> --to json --debug   # → out/<file>__<borehole>.json
```

| Option | Meaning |
|---|---|
| `inputs` | files (`.pdf`, `.png`, `.jpg`, `.tif`, `.docx`) or folders, searched recursively |
| `--to` | `print` (default) to the terminal, `json` to one file per borehole, `api` to POST to the API |
| `--out-dir DIR` | where `--to json` writes (default `out/`) |
| `--api-url URL` | API base URL for `--to api`, default `http://localhost:4000/api` |
| `--debug` | save the intermediate stage results under `output/` |

- A file that fails is logged and skipped; the run exits with an error listing the failed files.
- `--to api` (ADR-0032, `src/bem/api.py`): each borehole is created with `POST /api/boreholes`. If the
  input file is named `<document_id>.<ext>` (what `mix documents.backfill` produces, ADR-0014), the
  borehole is linked to that document and every stage result is reported with the `PUT` endpoints
  (see [`API_INTEGRATION.md`](API_INTEGRATION.md)). Other file names only create the borehole, with a warning.
- The borehole payload (`Borehole.to_api_dict()` in `src/bem/schema.py`) puts `source_file` and
  `translate_errors` into `metadata`, and leaves out the raw markdown. `--to api` wraps it as
  `{"borehole", "layers", "document_id"}`.

## 1. OCR (Docling): document → markdown

`src/bem/ocr.py` converts one PDF or image to markdown. Every page is OCR'd, even digital PDFs,
because the text layer loses table structure (ADR-0007, ADR-0008). `ocr_file(path)` returns the
markdown as a string and has no command-line interface, so use the full pipeline with `--debug`, or:

```bash
uv run python -c "
from pathlib import Path
from bem.ocr import ocr_file
path = Path('../data/BoreholeData/<folder>/<report>.pdf')
out = Path('output/ocr') / f'{path.parent.name}__{path.stem}.md'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(ocr_file(path), encoding='utf-8')
"
```

- Output: `output/ocr/<parent-folder>__<file-name>.md` (the folder name is a prefix, because different
  reports share file names such as `Report01.pdf`; `--debug` uses the same names).
- The first run downloads the Docling and EasyOCR models, so it is slow.
- Quick check with Docling's default settings (no forced OCR), printing to the terminal or a file:
  ```bash
  uv run python tests/docling_test.py <file.pdf>
  uv run python tests/docling_test.py <file.pdf> -o output/ocr/<name>.md
  ```

## 2. Translation: markdown → English with standard keys

Translates labels and values to English and maps labels to the borehole format keys (ADR-0017 to
ADR-0020). Values it cannot translate are marked `translate_error:<text>`.

```bash
# once, while online: download the local MarianMT translation models (ADR-0018)
uv run python -m bem.translation_and_labeling.download_models

# translate every output/ocr/*.md → output/translate/*.md
uv run python tests/translation_test.py

# same, but make sure nothing is fetched from the internet
HF_HUB_OFFLINE=1 uv run python tests/translation_test.py
```

- It prints the number of `translate_error` values per file and lists them.
- It is a script, not a pytest test: it has no assertions.

## 3. Extraction (Qwen): translated markdown → JSON

In the full pipeline, `extract(section)` in `src/bem/extraction/extract.py` does this for each triaged
borehole. The command below runs it on one translated file on its own (no triage).

Sends one translated file to a Qwen model behind an OpenAI-compatible server, validates the result,
and writes JSON in the backend's shape (`boreholes` + `borehole_layers`, ADR-0012, ADR-0023).

Start a model server first (default: Ollama):

```bash
ollama pull qwen3.5:2b      # once
ollama serve                # skip if already running; check with `ollama ps`
```

Run the extraction on one translated file:

```bash
uv run python -m bem.extraction output/translate/AF01.md              # → output/extraction/AF01.json
uv run python -m bem.extraction output/translate/AF01.md --markdown   # also → AF01.md (readable tables)
uv run python -m bem.extraction output/translate/AF01.md --out-dir results
```

| Option | Meaning |
|---|---|
| `input` | translated text or markdown file (one borehole report) |
| `--out-dir DIR` | output folder (default `output/extraction`) |
| `--markdown` | also write the record as markdown tables |
| `--model NAME` | model name (default from `settings.toml`, `qwen3.5:2b`) |
| `--base-url URL` | OpenAI-compatible server (default `http://localhost:11434/v1`) |
| `--prompt-file FILE` | system prompt file, for trying a prompt without editing the default |

Using a larger Qwen on a vLLM server:

```bash
vllm serve Qwen/Qwen3-32B --port 8000
uv run python -m bem.extraction output/translate/AF01.md \
  --model Qwen/Qwen3-32B --base-url http://localhost:8000/v1
```

The output JSON has `source_file`, `model`, `extracted_at`, `status` (`ok`, `warning` or `error`),
`issues`, and `record`. `record` is the borehole in the API's shape, with layers numbered by `position`.

### Configuration

Edit these files in `src/bem/extraction/`, no code changes needed:

| File | What it holds |
|---|---|
| `config/system_prompt.md` | the system prompt sent to Qwen |
| `config/settings.toml` | model name, server URL, temperature, Qwen thinking on/off, retries |
| `schema.py` | the JSON output format (Pydantic model). Its field descriptions are part of what the model sees |
| `validate.py` | consistency and grounding checks, and the `KNOWN_*` vocabularies |

## Run the stages by hand for one report

```bash
uv run python -c "from pathlib import Path; from bem.ocr import ocr_file; p = Path('../data/BoreholeData/<folder>/<report>.pdf'); o = Path('output/ocr/<folder>__<report>.md'); o.parent.mkdir(parents=True, exist_ok=True); o.write_text(ocr_file(p), encoding='utf-8')"
uv run python tests/translation_test.py
uv run python -m bem.extraction output/translate/<folder>__<report>.md --markdown
```
