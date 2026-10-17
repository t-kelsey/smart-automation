"""Thin wrapper around `claude -p` that returns structured output plus usage."""

import json
import pathlib
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field

from .naming import run_id


class PipelineError(RuntimeError):
    pass


# Set by the entry point; failed raw CLI responses are saved here for debugging.
DEBUG_DIR: pathlib.Path | None = None
ATTEMPTS = 2


def log(msg: str) -> None:
    """Progress output goes to stderr so stdout stays free for results."""
    print(f"[info] {msg}", file=sys.stderr, flush=True)


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_tokens: int = 0
    cost_usd: float = 0.0
    api_seconds: float = 0.0
    models: set[str] = field(default_factory=set)

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_create_tokens
        )

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_create_tokens += other.cache_create_tokens
        self.cost_usd += other.cost_usd
        self.api_seconds += other.api_seconds
        self.models |= other.models

    def to_dict(self) -> dict:
        d = asdict(self)
        d["models"] = sorted(self.models)
        d["total_tokens"] = self.total_tokens
        return d


@dataclass
class StepReport:
    """Wall time and summed usage of all Claude calls made by one pipeline step."""

    name: str
    model: str
    effort: str
    wall_seconds: float = 0.0
    usage: Usage = field(default_factory=Usage)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, usage: Usage) -> None:
        with self._lock:  # steps may run their calls in parallel threads
            self.usage.add(usage)

    def to_dict(self) -> dict:
        return {
            "step": self.name,
            "model_requested": self.model,
            "effort": self.effort,
            "wall_seconds": round(self.wall_seconds, 2),
            **self.usage.to_dict(),
        }


class Timer:
    def __init__(self, report: StepReport):
        self.report = report

    def __enter__(self):
        self.start = time.monotonic()
        return self.report

    def __exit__(self, *exc):
        self.report.wall_seconds = time.monotonic() - self.start


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


def run_claude(
    prompt: str,
    *,
    model: str,
    effort: str,
    schema: dict,
    report: StepReport,
    tools: str = "Read",
    add_dirs: list[pathlib.Path] | None = None,
    max_turns: int = 8,
) -> dict:
    """Run one `claude -p` call, add its usage to `report`, return the structured output.

    `tools=""` disables all tools (pure text-in/text-out step).
    """
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
        _save_debug(r.stdout)
        log(f"{last_error}, attempt {attempt}/{ATTEMPTS}" + (", retrying" if attempt < ATTEMPTS else ""))
    raise PipelineError(f"{last_error}; raw response saved in {DEBUG_DIR or '(no debug dir set)'}")


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


def _save_debug(raw: str) -> None:
    if DEBUG_DIR is None:
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    n = len(list(DEBUG_DIR.glob("*failed_response_*.json"))) + 1
    (DEBUG_DIR / f"{run_id()}_failed_response_{n:02d}.json").write_text(raw)
