"""Local vision-language backend of the AI interface (Ollama `/api/chat`, ADR-0040).

A chat endpoint cannot open files like the Claude CLI's Read tool, so the PDF pages named in `inputs`
are rendered to PNG (poppler's `pdftoppm`) and sent base64-encoded. The JSON schema goes in `format`
(grammar-constrained decoding); the answer is still re-parsed and retried on bad JSON.

Env: BEM_LOCAL_URL (required, e.g. http://localhost:11434), BEM_LOCAL_MODEL (fallback model name),
BEM_LOCAL_TIMEOUT (s), BEM_LOCAL_NUM_CTX, BEM_LOCAL_MAX_SIDE (px of the longer page side),
BEM_LOCAL_MAX_PAGES (pages per request).
"""

import base64
import os
import pathlib
import subprocess
import tempfile
import time

import httpx

from .ai import AI, PipelineError, StepReport, Usage, log
from .jsonutil import ATTEMPTS, json_from_text, save_debug

TRANSPORT_ATTEMPTS = 3


def is_configured() -> bool:
    return bool(os.environ.get("BEM_LOCAL_URL", "").strip())


def max_pages() -> int:
    return int(os.environ.get("BEM_LOCAL_MAX_PAGES", "4"))


def parse_range(spec: str) -> tuple[int, int]:
    """'3' -> (3, 3), '1-4' -> (1, 4); 1-based, inclusive."""
    first, _, last = spec.partition("-")
    a, b = int(first), int(last or first)
    if a < 1 or b < a:
        raise PipelineError(f"invalid page range {spec!r}")
    return a, b


def render_pages(pdf: pathlib.Path, spec: str, max_side: int) -> list[str]:
    """Render the pages of `pdf` to PNG and return them base64-encoded, in page order."""
    first, last = parse_range(spec)
    with tempfile.TemporaryDirectory(prefix="bem-img-") as tmp:
        prefix = pathlib.Path(tmp) / "p"
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-scale-to", str(max_side), "-f", str(first), "-l", str(last), str(pdf), str(prefix)],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError as e:
            raise PipelineError("pdftoppm not found: install poppler") from e
        except subprocess.CalledProcessError as e:
            raise PipelineError(f"pdftoppm failed on {pdf.name}: {e.stderr.decode(errors='replace').strip()}") from e
        return [base64.b64encode(f.read_bytes()).decode() for f in sorted(pathlib.Path(tmp).glob("p-*.png"))]


class LocalVLM(AI):
    reads_files = False

    @property
    def max_input_pages(self) -> int:  # type: ignore[override]
        return max_pages()

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport  # tests inject httpx.MockTransport

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
        inputs: list[tuple[pathlib.Path, str]] | None = None,
    ) -> dict:
        """One chat call with the page images attached; `effort`, `tools`, `add_dirs`, `max_turns` are ignored."""
        base_url = os.environ.get("BEM_LOCAL_URL", "").strip().rstrip("/")
        if not base_url:
            raise PipelineError("BEM_LOCAL_URL is not set")
        model = model or os.environ.get("BEM_LOCAL_MODEL", "")
        if not model:
            raise PipelineError("no local model given (step config or BEM_LOCAL_MODEL)")

        images: list[str] = []
        for pdf, spec in inputs or []:
            first, last = parse_range(spec)
            if last - first + 1 > max_pages():
                raise PipelineError(
                    f"{pdf.name}: {last - first + 1} pages exceed BEM_LOCAL_MAX_PAGES={max_pages()} of the local backend"
                )
            images += render_pages(pdf, spec, int(os.environ.get("BEM_LOCAL_MAX_SIDE", "1100")))

        message: dict = {"role": "user", "content": prompt}
        if images:
            message["images"] = images
        body = {
            "model": model,
            "messages": [message],
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0, "num_ctx": int(os.environ.get("BEM_LOCAL_NUM_CTX", "8192"))},
        }

        last_error = ""
        for attempt in range(1, ATTEMPTS + 1):
            out = self._post(base_url, body)
            report.add(
                Usage(
                    calls=1,
                    input_tokens=out.get("prompt_eval_count") or 0,
                    output_tokens=out.get("eval_count") or 0,
                    api_seconds=(out.get("total_duration") or 0) / 1e9,
                    models={model},
                )
            )
            content = (out.get("message") or {}).get("content")
            data = json_from_text(content)
            if data is not None:
                return data
            last_error = f"no valid JSON in local model answer (done_reason={out.get('done_reason')})"
            save_debug(self.debug_dir, content if isinstance(content, str) else repr(out))
            log(f"{last_error}, attempt {attempt}/{ATTEMPTS}" + (", retrying" if attempt < ATTEMPTS else ""))
        raise PipelineError(f"{last_error}; raw response saved in {self.debug_dir or '(no debug dir set)'}")

    def _post(self, base_url: str, body: dict) -> dict:
        timeout = float(os.environ.get("BEM_LOCAL_TIMEOUT", "600"))
        for attempt in range(1, TRANSPORT_ATTEMPTS + 1):
            try:
                with httpx.Client(transport=self._transport, timeout=timeout) as client:
                    r = client.post(f"{base_url}/api/chat", json=body)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as e:
                # 4xx (unknown model, bad request) will not get better by retrying
                raise PipelineError(f"local model server answered {e.response.status_code}: {e.response.text[:500]}") from e
            except httpx.TransportError as e:
                if attempt == TRANSPORT_ATTEMPTS:
                    raise PipelineError(f"local model server unreachable at {base_url}: {e!r}") from e
                log(f"local model server error {e!r}, retry {attempt}/{TRANSPORT_ATTEMPTS - 1}")
                time.sleep(2 * attempt)
        raise AssertionError("unreachable")
