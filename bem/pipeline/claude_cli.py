"""`claude -p` backend of the AI interface: returns structured output plus usage."""

import json
import pathlib
import subprocess

from .ai import AI, PipelineError, StepReport, Usage, log
from .naming import run_id

ATTEMPTS = 2


def _usage_from(out: dict) -> Usage:
    u = out.get("usage") or {}
    return Usage(
        calls=1,
        input_tokens=u.get("input_tokens", 0),
        output_tokens=u.get("output_tokens", 0),
        cache_read_tokens=u.get("cache_read_input_tokens", 0),
        cache_create_tokens=u.get("cache_creation_input_tokens", 0),
        cost_usd=out.get("total_cost_usd") or 0.0,
        api_seconds=(out.get("duration_api_ms") or 0) / 1000,
        models=set((out.get("modelUsage") or {}).keys()),
    )


class ClaudeCLI(AI):
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
        files: list[pathlib.Path] | None = None,  # unused: the CLI reads files itself via the Read tool
    ) -> dict:
        """Run one `claude -p` call, add its usage to `report`, return the structured output.

        `tools=""` disables all tools (pure text-in/text-out step).
        """
        return _run_claude(self, prompt, model, effort, schema, report, tools, add_dirs, max_turns)


def _run_claude(ai, prompt, model, effort, schema, report, tools, add_dirs, max_turns) -> dict:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema),
        "--model",
        model,
        "--effort",
        effort,
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
        "--tools",
        tools,
    ]
    if tools:
        cmd += ["--allowedTools", tools]
    for d in add_dirs or []:
        cmd += ["--add-dir", str(d)]

    last_error = ""
    for attempt in range(1, ATTEMPTS + 1):
        report.raise_if_stopped()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            # with --output-format json the CLI reports errors on stdout, not stderr
            raise PipelineError(
                f"claude exited with {e.returncode}\n"
                f"stderr: {e.stderr.strip() or '(empty)'}\n"
                f"stdout: {e.stdout.strip()[:2000] or '(empty)'}"
            ) from e

        out = json.loads(r.stdout)
        report.add(_usage_from(out))  # failed attempts cost money too
        if out.get("is_error"):
            raise PipelineError(f"CLI reported an error: {out.get('subtype')}: {out.get('result')}")
        data = out.get("structured_output")
        if data is None:  # model answered in prose instead of the schema tool
            data = _json_from_text(out.get("result"))
        if data is not None:
            return data

        last_error = f"no structured output (stop_reason={out.get('stop_reason')})"
        _save_debug(ai.debug_dir, r.stdout)
        log(f"{last_error}, attempt {attempt}/{ATTEMPTS}" + (", retrying" if attempt < ATTEMPTS else ""))
    raise PipelineError(f"{last_error}; raw response saved in {ai.debug_dir or '(no debug dir set)'}")


def _json_from_text(text: object) -> dict | None:
    """Pull a JSON object out of a plain-text answer (optionally in a ```json fence)."""
    if not isinstance(text, str):
        return None
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _save_debug(debug_dir: pathlib.Path | None, raw: str) -> None:
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(debug_dir.glob("*failed_response_*.json"))) + 1
    (debug_dir / f"{run_id()}_failed_response_{n:02d}.json").write_text(raw)
