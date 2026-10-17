"""Helpers shared by the AI backends: JSON extraction from prose and debug dumps of failed answers."""

import json
import pathlib

from .naming import run_id

ATTEMPTS = 2


def json_from_text(text: object) -> dict | None:
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


def save_debug(debug_dir: pathlib.Path | None, raw: str) -> None:
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(debug_dir.glob("*failed_response_*.json"))) + 1
    (debug_dir / f"{run_id()}_failed_response_{n:02d}.json").write_text(raw)
