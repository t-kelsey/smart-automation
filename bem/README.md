# bem – borehole extraction pipeline

Pipeline (ADR-0001): **OCR → translation → extraction (Qwen) → JSON**. Each stage reads and
writes files under `output/`, so you can run and inspect them one at a time:

```
data/…/report.pdf ──ocr──▶ output/ocr/*.md ──translate──▶ output/translate/*.md ──qwen──▶ output/extraction/*.json
```

Once these stages work end to end, see [`API_INTEGRATION.md`](API_INTEGRATION.md) for how to
report OCR/translation/triage/extraction results and the final boreholes to `api/`.

All commands run from this folder (`bem/`) with [uv](https://docs.astral.sh/uv/). The first
`uv run` creates `.venv` and installs the dependencies from `uv.lock`.

```bash
cd bem
uv sync
```

`uv run bem` (the full pipeline in `src/bem/main.py`) is not wired up yet. Run the stages below instead.

## 1. OCR (Docling): document → markdown

`src/bem/ocr.py` converts one PDF or image to markdown. Every page is OCR'd, even digital PDFs,
because the text layer loses table structure (ADR-0007, ADR-0008). It has no command-line
interface yet, so call the function:

```bash
uv run python -c "
from pathlib import Path
from bem.ocr import ocr_file
print(ocr_file(Path('../data/BoreholeData/<folder>/<report>.pdf'), Path('output/ocr')))
"
```

- Output: `output/ocr/<parent-folder>__<file-name>.md` (the folder name is a prefix, because different
  reports share file names such as `Report01.pdf`).
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

## Run everything for one report

```bash
uv run python -c "from pathlib import Path; from bem.ocr import ocr_file; ocr_file(Path('../data/BoreholeData/<folder>/<report>.pdf'), Path('output/ocr'))"
uv run python tests/translation_test.py
uv run python -m bem.extraction output/translate/<folder>__<report>.md --markdown
```
