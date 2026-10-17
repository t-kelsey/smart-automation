"""Per-step model/effort settings of a pipeline run (sent by the API in `POST /execute`)."""

from pydantic import BaseModel, ConfigDict

STEPS = ("filter", "split", "extract", "transform")


class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Hints interpreted by the AI backend (claude_cli: haiku/sonnet/opus, low/medium/high/xhigh/max).
    model: str
    effort: str


class PipelineConfig(BaseModel):
    """Every step may be omitted; it then uses its default."""

    model_config = ConfigDict(extra="forbid")

    filter: StepConfig = StepConfig(model="haiku", effort="high")
    split: StepConfig = StepConfig(model="haiku", effort="medium")
    extract: StepConfig = StepConfig(model="sonnet", effort="high")
    transform: StepConfig = StepConfig(model="haiku", effort="high")
