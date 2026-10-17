"""Step 1: translated OCR text -> Borehole, using a Qwen model behind an OpenAI-compatible server.

Example server (vLLM):
    vllm serve Qwen/Qwen3-32B --port 8000
Any server that supports `response_format={"type": "json_schema"}` works
(vLLM, SGLang, llama.cpp server, Ollama's OpenAI endpoint, ...).
"""
from __future__ import annotations

import logging

from openai import OpenAI
from pydantic import ValidationError

from ..schema import Borehole as PipelineBorehole
from .config import load_prompt, load_settings
from .schema import Borehole
from .validate import check_all, status

log = logging.getLogger("bem")


def make_client(base_url: str | None = None, api_key: str | None = None) -> OpenAI:
    """OpenAI-compatible client; defaults come from config/settings.toml."""
    cfg = load_settings()["model"]
    return OpenAI(base_url=base_url or cfg["base_url"], api_key=api_key or cfg["api_key"])


def extract_record(
    text: str,
    client: OpenAI,
    model: str | None = None,
    system_prompt: str | None = None,
    max_retries: int | None = None,
) -> Borehole:
    """Run the extraction. Retries only if the output fails Pydantic parsing
    (rare with constrained decoding, e.g. an unparseable date)."""
    cfg = load_settings()["model"]
    model = model or cfg["name"]
    max_retries = cfg["max_retries"] if max_retries is None else max_retries
    schema = Borehole.model_json_schema()
    messages = [
        {"role": "system", "content": system_prompt or load_prompt()},
        {"role": "user", "content": f"OCR text:\n\n{text}"},
    ]
    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=cfg["temperature"],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "borehole", "strict": True, "schema": schema},
            },
            # Qwen3 hybrid models: switch off thinking mode. Other models ignore this.
            extra_body={"chat_template_kwargs": {"enable_thinking": cfg["enable_thinking"]}},
        )
        content = resp.choices[0].message.content or ""
        try:
            return Borehole.model_validate_json(content)
        except ValidationError as e:
            last_error = e
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"The JSON was invalid: {e}\nReturn a corrected JSON object."},
            ]
    raise RuntimeError(f"Extraction failed after retries: {last_error}")


def extract(section: PipelineBorehole, client: OpenAI | None = None) -> PipelineBorehole:
    """Pipeline step: fill a triaged Borehole (name, source_file, raw_markdown) from its text.

    Returns a new pipeline Borehole shaped for the API sink. Triage provenance
    (source_file, raw_markdown, translate_errors) is carried over. The record stays
    `verified=False`; validation issues are logged, not raised, so that one doubtful
    record does not stop the run.
    """
    text = section.raw_markdown
    record = extract_record(text, client or make_client())
    record.layers.sort(key=lambda l: l.depth_from_m)  # the consistency checks expect depth order
    issues = check_all(record, text)
    for issue in issues:
        log.warning("%s: [%s] %s: %s", section.name, issue.level, issue.field, issue.message)
    log.info("%s: extracted %d layer(s), status %s", section.name, len(record.layers), status(issues))

    return record.to_pipeline(section)
