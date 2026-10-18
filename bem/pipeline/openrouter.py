"""OpenRouter backend of the AI interface: remote vision models over the OpenAI-compatible API.

Needs `OPENROUTER_API_KEY` in the environment (bem/.env). Unlike the `claude` CLI there is no Read
tool, so the pages of every PDF in `files` are rendered with `pdftoppm` and attached as images.
"""

import base64
import json
import os
import pathlib
import subprocess
import tempfile
import time

import httpx

from .ai import AI, PipelineError, StepReport, Usage, log
from .claude_cli import _json_from_text, _save_debug

ATTEMPTS = 3  # one may be spent on the json_object fallback
DEFAULT_URL = "https://openrouter.ai/api/v1"
RENDER_DPI = 110
TIMEOUT = 600.0

# The default step configs name Claude aliases; they resolve to these OpenRouter model ids.
# Any model containing "/" (e.g. "google/gemini-2.5-flash") is passed through unchanged, and
# BEM_OPENROUTER_MODEL forces one model for every step.
ALIASES = {
    "haiku": "anthropic/claude-haiku-4.5",
    "sonnet": "anthropic/claude-sonnet-4.5",
    "opus": "anthropic/claude-opus-4.5",
}
EFFORTS = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}

FILE_NOTE = """

[Attached: the pages of {names} as images, in page order. You cannot read files or call tools:
wherever the instructions above say to read a file or use the Read tool, use the attached page
images instead. Page numbers are 1-based within each file.]"""

SCHEMA_NOTE = "\n\nReply with a single JSON object (no prose, no code fence) matching this JSON schema:\n"


def resolve_model(model: str) -> str:
    return os.environ.get("BEM_OPENROUTER_MODEL") or ALIASES.get(model, model)


def render_pages(pdf: pathlib.Path) -> list[bytes]:
    """JPEG bytes of every page of `pdf`."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = pathlib.Path(tmp) / "p"
        try:
            subprocess.run(
                ["pdftoppm", "-jpeg", "-r", str(RENDER_DPI), str(pdf), str(prefix)],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError as e:
            raise PipelineError("pdftoppm not found; install poppler (brew install poppler)") from e
        except subprocess.CalledProcessError as e:
            raise PipelineError(f"pdftoppm failed on {pdf.name}: {e.stderr.decode(errors='replace')}") from e
        return [p.read_bytes() for p in sorted(pathlib.Path(tmp).glob("p-*.jpg"))]


def _usage_from(out: dict, seconds: float) -> Usage:
    u = out.get("usage") or {}
    details = u.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens") or 0
    return Usage(
        calls=1,
        input_tokens=max((u.get("prompt_tokens") or 0) - cached, 0),
        output_tokens=u.get("completion_tokens") or 0,
        cache_read_tokens=cached,
        cache_create_tokens=details.get("cache_write_tokens") or 0,
        cost_usd=u.get("cost") or 0.0,
        api_seconds=seconds,
        models={out["model"]} if out.get("model") else set(),
    )


class OpenRouter(AI):
    def __init__(self) -> None:
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", DEFAULT_URL).rstrip("/")
        self.json_schema = True  # cleared once a provider rejects the schema

    def _api_key(self) -> str:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise PipelineError("OPENROUTER_API_KEY is not set (add it to bem/.env)")
        return key

    def _content(self, prompt: str, schema: dict, files: list[pathlib.Path]) -> list[dict]:
        text = prompt + SCHEMA_NOTE + json.dumps(schema)
        content: list[dict] = []
        if files:
            text += FILE_NOTE.format(names=", ".join(f.name for f in files))
        content.append({"type": "text", "text": text})
        for f in files:
            for i, jpeg in enumerate(render_pages(f), 1):
                content.append({"type": "text", "text": f"{f.name} page {i}:"})
                b64 = base64.b64encode(jpeg).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        return content

    def run(
        self,
        prompt: str,
        *,
        model: str,
        effort: str,
        schema: dict,
        report: StepReport,
        tools: str = "Read",
        add_dirs: list[pathlib.Path] | None = None,
        max_turns: int = 8,
        files: list[pathlib.Path] | None = None,
    ) -> dict:
        key = self._api_key()
        body = {
            "model": resolve_model(model),
            "messages": [{"role": "user", "content": self._content(prompt, schema, files or [])}],
            "response_format": (
                {"type": "json_schema", "json_schema": {"name": "answer", "strict": False, "schema": schema}}
                if self.json_schema
                else {"type": "json_object"}
            ),
            "reasoning": {"effort": EFFORTS.get(effort, "medium")},
            "usage": {"include": True},
        }
        headers = {"Authorization": f"Bearer {key}"}

        last_error = ""
        for attempt in range(1, ATTEMPTS + 1):
            report.raise_if_stopped()
            start = time.monotonic()
            try:
                r = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=TIMEOUT)
            except httpx.HTTPError as e:
                last_error = f"request failed: {e!r}"
            else:
                if r.status_code != 200:
                    last_error = f"OpenRouter returned {r.status_code}: {r.text[:2000]}"
                    if r.status_code == 400 and "schema" in r.text.lower() and body["response_format"]["type"] == "json_schema":
                        # providers cap schema complexity (e.g. 16 nullable fields); the prompt already
                        # carries the schema, so fall back to plain JSON mode for this and later calls
                        log("provider rejected the response schema, falling back to json_object mode")
                        self.json_schema = False
                        body["response_format"] = {"type": "json_object"}
                        continue
                    if r.status_code < 500 and r.status_code != 429:
                        raise PipelineError(last_error)  # bad key, bad model, no credit: retrying won't help
                else:
                    out = r.json()
                    report.add(_usage_from(out, time.monotonic() - start))  # failed attempts cost too
                    if out.get("error"):
                        last_error = f"OpenRouter error: {out['error']}"
                    else:
                        choice = (out.get("choices") or [{}])[0]
                        data = _json_from_text((choice.get("message") or {}).get("content"))
                        if data is not None:
                            return data
                        last_error = f"no JSON in answer (finish_reason={choice.get('finish_reason')})"
                        _save_debug(self.debug_dir, r.text)
            log(f"{last_error}, attempt {attempt}/{ATTEMPTS}" + (", retrying" if attempt < ATTEMPTS else ""))
            if attempt < ATTEMPTS:
                time.sleep(2)
        raise PipelineError(last_error)
