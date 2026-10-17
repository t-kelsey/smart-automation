"""Editable extraction config: settings.toml (model, server) and system_prompt.md (prompt).

The JSON output format is the Pydantic model in ../schema.py (shaped like the backend). Its field
descriptions are part of what the model sees, so edit them there.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.toml", "rb") as f:
        settings = tomllib.load(f)
    # Environment overrides, e.g. to reach a model server outside the container.
    for key, var in (("name", "BEM_MODEL_NAME"), ("base_url", "BEM_MODEL_BASE_URL"), ("api_key", "BEM_MODEL_API_KEY")):
        if os.environ.get(var):
            settings["model"][key] = os.environ[var]
    return settings


def load_prompt(path: Path | None = None) -> str:
    """Read the system prompt: `path` if given, else the file named in settings.toml."""
    if path is None:
        path = CONFIG_DIR / load_settings()["prompt"]["file"]
    return Path(path).read_text(encoding="utf-8").strip()
