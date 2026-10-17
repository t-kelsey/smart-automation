import pathlib
import re
from datetime import datetime

_PREFIX = re.compile(r"^\d{8}-\d{6}_")

# One id per pipeline execution, shared by every file it writes.
_run_id: str | None = None


def run_id() -> str:
    global _run_id
    if _run_id is None:
        _run_id = f"{datetime.now():%Y%m%d-%H%M%S}"
    return _run_id


def stamped(path: pathlib.Path) -> pathlib.Path:
    """`dir/name.ext` -> `dir/<run id>_name.ext`."""
    return path.with_name(f"{run_id()}_{_PREFIX.sub('', path.name)}")


def base(stem: str) -> str:
    """Strip the run id prefix, e.g. to name derived files after `borehole_01`."""
    return _PREFIX.sub("", stem)
