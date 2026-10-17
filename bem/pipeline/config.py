"""Per-step model/effort settings of a pipeline run (sent by the API in `POST /execute`)."""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict

STEPS = ("filter", "split", "extract", "transform")

CLAUDE_MODELS = frozenset({"haiku", "sonnet", "opus"})
# Used when provider is "local" and a step still carries a Claude model name (e.g. the UI default);
# env BEM_LOCAL_MODEL overrides them for all steps.
LOCAL_DEFAULT_MODELS = {
    "filter": "qwen3-vl:2b",
    "split": "qwen3-vl:2b",
    "extract": "qwen3-vl:4b",
    "transform": "qwen3-vl:4b",
}


class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Hints interpreted by the AI backend (claude_cli: haiku/sonnet/opus, low/medium/high/xhigh/max).
    model: str
    effort: str


class PipelineConfig(BaseModel):
    """Every step may be omitted; it then uses its default."""

    model_config = ConfigDict(extra="forbid")

    # One AI provider per run: "claude" (claude CLI, default) or "local" (Ollama vision model).
    provider: Literal["claude", "local"] = "claude"

    filter: StepConfig = StepConfig(model="haiku", effort="high")
    split: StepConfig = StepConfig(model="haiku", effort="medium")
    extract: StepConfig = StepConfig(model="sonnet", effort="high")
    transform: StepConfig = StepConfig(model="haiku", effort="high")


def resolve_models(config: PipelineConfig) -> dict[str, StepConfig]:
    """The effective per-step settings. For `local`, Claude model names are swapped for local defaults."""
    out = {}
    for step in STEPS:
        sc = getattr(config, step)
        if config.provider == "local" and sc.model in CLAUDE_MODELS:
            sc = StepConfig(model=os.environ.get("BEM_LOCAL_MODEL") or LOCAL_DEFAULT_MODELS[step], effort=sc.effort)
        out[step] = sc
    return out


def default_chunk_size(provider: str) -> int:
    """Pages per classification call in step 1: small for the local backend (small context window)."""
    if provider == "local":
        return int(os.environ.get("BEM_LOCAL_CHUNK_SIZE", "2"))
    return int(os.environ.get("BEM_CHUNK_SIZE", "10"))
