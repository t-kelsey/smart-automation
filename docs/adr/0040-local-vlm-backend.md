---
id: ADR-0040
date: 2026-10-17
author: claude
title: Selectable local vision-language backend (Ollama, Qwen3-VL)
---

# ADR-0040 – Selectable local vision-language backend

## Context

All model calls of the `bem` pipeline go through `AI.run()` and the only backend was `ClaudeCLI`, which reads PDFs with the CLI's Read tool. ADR-0001 rejected a local vision model, ADR-0018 added a local backend for translation only. The borehole logs in `data/` are confidential, so a run that never leaves the machine is valuable. The dev machine has a 4 GB GPU (RTX A500), which rules out anything above roughly 4B parameters.

## Decision

- `PipelineConfig.provider` (`claude` default, or `local`) selects the backend for one run. It travels unchanged through the web config, `pipeline_runs.config` and `POST /execute`, so the Elixir API needs no change.
- New backend `bem/pipeline/local_vlm.py` talks to [Ollama](https://ollama.com) `/api/chat` over `httpx`. Because a chat endpoint cannot open files, `AI.run()` got an optional `inputs=[(pdf, "1-3")]`: the local backend renders those pages with `pdftoppm` and attaches them as base64 images; the Claude backend ignores `inputs` and keeps its prompts byte-identical. Each prompt has a backend-neutral variant (`*_PROMPT_LOCAL`) chosen via `AI.reads_files`.
- The JSON schemas from `schemas.py` are passed as Ollama's `format` (constrained decoding); the answer is re-parsed and retried on bad JSON, transport errors are retried with backoff. Usage is filled from Ollama's token counts, cost is 0.
- Models per step: `qwen3-vl:2b` for filter and split, `qwen3-vl:4b` for extract and transform (`LOCAL_DEFAULT_MODELS`). They replace Claude names (`haiku|sonnet|opus`) only; `BEM_LOCAL_MODEL` overrides the default for all steps.
- Backends are created per run (`new_ai`) and passed down to the steps instead of using the process-wide singleton, so runs do not share `debug_dir`. `--ai`/`BEM_AI` and `set_ai()` still work.
- `/execute` returns 422 for `provider: "local"` without `BEM_LOCAL_URL`.
- Small context: step 1 uses 2 pages per call (`BEM_LOCAL_CHUNK_SIZE`), step 2 fails above `BEM_LOCAL_MAX_PAGES` (default 4) pages, step 3 reads only the first pages and adds a warning. `StepReport` now carries the provider.

## Pros

- No data leaves the machine, no per-token cost.
- Claude path unchanged; providers are chosen per run.
- Server and model are configurable by env.

## Cons

- 2B/4B models read colour and hatch patterns and long multi-page logs much worse than Claude; step 4 (large schema, DIN 4023 vocabulary) is the weakest, `din4023.conform` only repairs part of it.
- Page limits mean long documents fail (split) or are truncated (extract) in local mode.
- The backend depends on Ollama's request shape (`format`, `images`, `think`).

## Alternatives

- vLLM or llama.cpp `llama-server` (OpenAI-style `response_format`): better throughput, but no automatic CPU offload on 4 GB (vLLM) or more setup; the backend could be adapted later.
- A larger model (Qwen3-VL-32B, InternVL3.5): better quality, needs about 24–80 GB VRAM.
- Local Claude-style agent loop with file tools: too heavy for small models.

## Consequences

- Revisits the "local vision model" alternative of ADR-0001 for the experiment; ADR-0001 and the README still describe `pipeline/steps.py` (now `pipeline/steps/`).
- Builds on ADR-0018 (local backend idea) and ADR-0039 (config reaches the pipeline).

## Findings from the first test runs (2026-10-17, RTX A500 4 GB, Ollama 0.40.5)

- **Verified:** the config reaches the pipeline (`provider: local` in `pipeline_runs.config`, `/execute` returns 422 without `BEM_LOCAL_URL`), step 1 (filter) works on real borehole PDFs, and a single filter call with `qwen3.5:2b` took about 17 s.
- **Open problem:** the default `qwen3-vl:2b` tag is the reasoning variant. Ollama keeps it reasoning despite `think: false` when `format` is set: the text lands in `message.thinking`, `message.content` stays empty and the call ends with `done_reason: length` after filling the whole `num_ctx` (8192). Step 2 (split) then failed after 2 empty answers and about 5 minutes (run `fbdea89b…`, both debug files 0 bytes).
- **Works:** the same split call with `qwen3.5:2b` answered correctly in 9 s (51 tokens). Setting `BEM_LOCAL_MODEL=qwen3.5:2b` is the quick workaround.
- **Next:** try a non-reasoning Qwen3-VL variant (an `-instruct` tag, name to be verified in the Ollama library) and update `LOCAL_DEFAULT_MODELS`, the web model list and this ADR; make `LocalVLM` fail fast on empty content with `done_reason: length` instead of retrying; steps 3 and 4 have not run yet, so extract and transform quality on 2B/4B models is still untested.
- **Ops notes:** the API does not read `api/.env`; `PIPELINE_URL` must be exported when starting `mix phx.server`, otherwise runs stay `new` ("No pipeline is configured"). In Docker the pipeline needs `BEM_LOCAL_URL` pointing at the host's Ollama (not `localhost`).

## References

- ADR-0001, ADR-0018, ADR-0039
