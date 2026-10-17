"""Deliver extracted boreholes to the Elixir API, to JSON files, or to the terminal (ADR-0001)."""

import json
import logging
import re
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from .api import ApiClient
from .schema import Borehole

log = logging.getLogger("bem")


def _file_stem(borehole: Borehole) -> str:
    """<source file stem>__<borehole id>, safe to use as a file name."""
    ident = borehole.external_id or borehole.name
    return re.sub(r"[^\w.-]+", "_", f"{Path(borehole.source_file).stem}__{ident}")


class ApiSink:
    """POST each borehole to the Elixir API (linked to its document if known), which writes it to PostGIS."""

    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def __call__(self, borehole: Borehole, document_id: str | None = None) -> str | None:
        """Returns the id of the created borehole. Raises requests.HTTPError if the API refuses it."""
        return self.client.post_borehole(borehole, document_id)["data"]["id"]


class JsonFileSink:
    """Save each borehole as its own JSON file, named <source>__<borehole_id>.json."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, borehole: Borehole, document_id: str | None = None) -> None:
        path = self.out_dir / f"{_file_stem(borehole)}.json"
        path.write_text(json.dumps(borehole.to_api_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("saved %s", path)


class PrintSink:
    """Print each borehole as indented JSON to the terminal."""

    def __call__(self, borehole: Borehole, document_id: str | None = None) -> None:
        print(json.dumps(borehole.to_api_dict(), indent=2, ensure_ascii=False))


def make_sink(to: str, client: ApiClient, out_dir: Path) -> AbstractContextManager:
    """Return a context manager that yields the sink selected by `to` (api, json or print)."""
    if to == "api":
        sink = ApiSink(client)
    elif to == "json":
        sink = JsonFileSink(out_dir)
    elif to == "print":
        sink = PrintSink()
    else:
        raise ValueError(f"unknown output target: {to}")
    return nullcontext(sink)
