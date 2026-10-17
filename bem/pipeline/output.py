"""Where stage results go: the API (via a `Tracker`) and, in dev only, local files below `out/`.

`BEM_ENV=dev` (default) keeps the JSON results, report and debug files on disk; `BEM_ENV=prod`
writes none of them. The intermediate PDFs that the model reads still need a scratch directory,
which `run_pipeline` creates temporarily in prod and deletes afterwards.
"""

import json
import os
import pathlib

from .ai import StepReport, log


class Tracker:
    """Receives the lifecycle of every stage (ADR-0040); the server reports it to the API.

    `position` is the 1-based borehole index for extract/transform and None for filter/split;
    `usage` is the stage's (or borehole's) `Usage.to_dict()`. The default does nothing (CLI runs).
    """

    def started(self, stage: str, position: int | None, model: str, effort: str) -> None:
        pass

    def succeeded(
        self, stage: str, position: int | None, data: dict, files: list[pathlib.Path], usage: dict | None
    ) -> None:
        """`files` are local PDFs the stage produced (split: one per borehole)."""

    def failed(self, stage: str, position: int | None, error: BaseException, usage: dict | None) -> None:
        pass


def persist_enabled() -> bool:
    return os.environ.get("BEM_ENV", "dev").lower() != "prod"


def dump_json(path: pathlib.Path, data) -> None:
    """Write `data` to `path` (dev only)."""
    if not persist_enabled():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class Recorder:
    """Called by every step when a stage (or one borehole of it) starts, succeeds or fails.

    Hands the events to the `Tracker`; tracking errors are logged, they never abort the extraction.
    """

    def __init__(self, tracker: Tracker | None = None):
        self.tracker = tracker or Tracker()

    def _notify(self, what: str, stage: str, position: int | None, call) -> None:
        try:
            call()
        except Exception as e:  # tracking must not abort the extraction
            log(f"{stage}{'' if position is None else f' #{position}'}: could not report {what}: {e}")

    def start(self, stage: str, report: StepReport, *, position: int | None = None) -> None:
        """Mark the stage running; raises PipelineStopped instead if the run was stopped."""
        report.raise_if_stopped()
        self._notify("start", stage, position, lambda: self.tracker.started(stage, position, report.model, report.effort))

    def record(
        self,
        stage: str,
        data: dict,
        *,
        report: StepReport | None = None,
        position: int | None = None,
        path: pathlib.Path | None = None,
        files: list[pathlib.Path] | None = None,
    ) -> None:
        """The stage produced `data`; `path` is where dev runs keep it locally."""
        if path is not None:
            dump_json(path, data)
        usage = report.usage.to_dict() if report is not None else None
        self._notify("result", stage, position, lambda: self.tracker.succeeded(stage, position, data, files or [], usage))

    def record_failure(
        self, stage: str, error: BaseException, *, report: StepReport | None = None, position: int | None = None
    ) -> None:
        """Report a failed (or stopped) stage with its reason, so failed runs can be analysed.

        Marks the exception as recorded so callers further up do not report it a second time.
        """
        if getattr(error, "stage_recorded", False):
            return
        try:
            error.stage_recorded = True  # type: ignore[attr-defined]
        except AttributeError:
            pass
        usage = report.usage.to_dict() if report is not None else None
        self._notify("failure", stage, position, lambda: self.tracker.failed(stage, position, error, usage))
