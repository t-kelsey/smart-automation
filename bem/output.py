"""Deliver extracted boreholes to the Elixir API, to JSON files, or to the terminal (ADR-0001)."""

import json
import logging
from contextlib import AbstractContextManager, nullcontext
from dataclasses import asdict
from pathlib import Path

import requests

from .models import Borehole

log = logging.getLogger("bem")


class ApiSink:
    """POST each borehole as JSON to the Elixir API, which writes it to PostGIS."""

    def __init__(self, url: str) -> None:
        self.url = url

    def __call__(self, borehole: Borehole) -> None:
        requests.post(self.url, json=asdict(borehole), timeout=30).raise_for_status()


class JsonFileSink:
    """Save each borehole as its own JSON file, named <source>__<borehole_id>.json."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, borehole: Borehole) -> None:
        record = asdict(borehole)
        path = self.out_dir / f"{Path(record['source']).stem}__{record['borehole_id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("saved %s", path)


class PrintSink:
    """Print each borehole as indented JSON to the terminal."""

    def __call__(self, borehole: Borehole) -> None:
        print(json.dumps(asdict(borehole), indent=2, ensure_ascii=False))


def make_sink(to: str, api_url: str, out_dir: Path) -> AbstractContextManager:
    """Return a context manager that yields the sink selected by `to` (api, json or print)."""
    if to == "api":
        sink = ApiSink(api_url)
    elif to == "json":
        sink = JsonFileSink(out_dir)
    elif to == "print":
        sink = PrintSink()
    else:
        raise ValueError(f"unknown output target: {to}")
    return nullcontext(sink)
