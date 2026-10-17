"""Where stage results go: the API (via `on_stage`) and, in dev only, local files below `out/`.

`BEM_ENV=dev` (default) keeps the JSON results, report and debug files on disk; `BEM_ENV=prod`
writes none of them. The intermediate PDFs that the model reads still need a scratch directory,
which `run_pipeline` creates temporarily in prod and deletes afterwards.
"""

import json
import os
import pathlib
from collections.abc import Callable

from .ai import log

# on_stage(stage, position, data, files): `files` are local PDFs the stage produced (split: one per borehole)
OnStage = Callable[[str, int | None, dict, list[pathlib.Path]], None]


def persist_enabled() -> bool:
    return os.environ.get("BEM_ENV", "dev").lower() != "prod"


def dump_json(path: pathlib.Path, data) -> None:
    """Write `data` to `path` (dev only)."""
    if not persist_enabled():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class Recorder:
    """Called by every step once it has produced its output."""

    def __init__(self, on_stage: OnStage | None = None):
        self.on_stage = on_stage

    def record(
        self,
        stage: str,
        data: dict,
        *,
        position: int | None = None,
        path: pathlib.Path | None = None,
        files: list[pathlib.Path] | None = None,
    ) -> None:
        """`position` is the 1-based borehole index for extract/transform, None for filter/split."""
        if path is not None:
            dump_json(path, data)
        if self.on_stage is not None:
            try:
                self.on_stage(stage, position, data, files or [])
            except Exception as e:  # tracking must not abort the extraction
                log(f"{stage}{'' if position is None else f' #{position}'}: could not upload stage result: {e}")

    def record_failure(self, stage: str, error: BaseException, *, position: int | None = None) -> None:
        """Store a failed step as an exec_stage whose `data` holds the reason, so failed runs can be analysed.

        Marks the exception as recorded so callers further up do not store it a second time.
        """
        if getattr(error, "stage_recorded", False):
            return
        try:
            error.stage_recorded = True  # type: ignore[attr-defined]
        except AttributeError:
            pass
        data = {"status": "failed", "error_type": type(error).__name__, "error": str(error)}
        self.record(stage, data, position=position)
