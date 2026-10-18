"""Backend-independent AI interface of the pipeline.

Steps talk to one general `AI` object (`get_ai()`); which model/provider sits behind it is chosen
by name (`--ai`, env `BEM_AI`, default `openrouter`, which needs OPENROUTER_API_KEY; `claude_cli` is for development). To add a backend, subclass `AI`, implement
`run`, and register it in `_BACKENDS`.
"""

import os
import pathlib
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

DEFAULT_BACKEND = "openrouter"


def log(msg: str) -> None:
    """Progress output goes to stderr so stdout stays free for results."""
    print(f"[info] {msg}", file=sys.stderr, flush=True)


class PipelineError(RuntimeError):
    pass


class PipelineStopped(PipelineError):
    """The run was cancelled (`POST /runs/:id/stop`); raised at the next stage, borehole or AI call."""


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
    # set to cancel the run; checked before every stage, borehole and AI call
    stop: threading.Event | None = field(default=None, repr=False)
    # a per-borehole report forwards its usage to the whole step's report
    parent: "StepReport | None" = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, usage: Usage) -> None:
        with self._lock:  # steps may run their calls in parallel threads
            self.usage.add(usage)
        if self.parent is not None:
            self.parent.add(usage)

    def child(self, suffix: str) -> "StepReport":
        """A report for one part of the step (e.g. one borehole) that also counts towards this one."""
        return StepReport(f"{self.name} {suffix}", self.model, self.effort, stop=self.stop, parent=self)

    def raise_if_stopped(self) -> None:
        if self.stop is not None and self.stop.is_set():
            raise PipelineStopped("run stopped")

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



class AI(ABC):
    """One structured-output model call. Implementations add their usage to `report` and call
    `report.raise_if_stopped()` before every model request so a stopped run ends quickly."""

    # Failed raw responses are saved here for debugging (set by the entry point).
    debug_dir: pathlib.Path | None = None

    @abstractmethod
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
        """Return the model's answer as a dict matching the JSON `schema`.

        `model` and `effort` are hints interpreted by the backend (for claude_cli: haiku/sonnet/opus
        and low..max). `tools`/`add_dirs`/`max_turns` describe file access for agentic backends;
        `tools=""` means a pure text-in/text-out call. `files` are the PDFs the prompt refers to by path;
        backends without file access (openrouter) attach their pages as images. Raise `PipelineError` on failure.
        """


_BACKENDS = {
    "claude_cli": lambda: _load("claude_cli", "ClaudeCLI"),
    "openrouter": lambda: _load("openrouter", "OpenRouter"),
}
_current: AI | None = None


def _load(module: str, cls: str) -> AI:
    import importlib

    return getattr(importlib.import_module(f".{module}", __package__), cls)()


def get_ai(name: str | None = None) -> AI:
    """The process-wide AI object. `name` (re)selects the backend; default env BEM_AI or openrouter."""
    global _current
    if name is not None or _current is None:
        name = name or os.environ.get("BEM_AI", DEFAULT_BACKEND)
        if name not in _BACKENDS:
            raise PipelineError(f"unknown AI backend {name!r}, available: {', '.join(sorted(_BACKENDS))}")
        debug_dir = _current.debug_dir if _current else None
        _current = _BACKENDS[name]()
        _current.debug_dir = debug_dir
    return _current


def set_ai(ai: AI) -> None:
    """Install a ready-made AI object (tests, custom backends)."""
    global _current
    _current = ai


def backend_names() -> list[str]:
    return sorted(_BACKENDS)
