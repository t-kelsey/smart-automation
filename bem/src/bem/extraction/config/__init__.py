"""Editable extraction config: settings.toml (model, server) and system_prompt.md (prompt).

The JSON output format is the Pydantic model in ../schema.py (shaped like the backend). Its field
descriptions are part of what the model sees, so edit them there.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.toml", "rb") as f:
        return tomllib.load(f)


def load_prompt(path: Path | None = None) -> str:
    """Read the system prompt: `path` if given, else the file named in settings.toml."""
    if path is None:
        path = CONFIG_DIR / load_settings()["prompt"]["file"]
    return Path(path).read_text(encoding="utf-8").strip()
