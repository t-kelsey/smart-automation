"""Report pipeline results to the Elixir API (bem/API_INTEGRATION.md, ADR-0030, ADR-0031).

Per document: PUT stage results (OCR, translation, triage), then per triage section PUT the
extraction result, POST the borehole and PUT the sink result. The tracking PUTs are debug
information, so a failed one is logged and never stops the run. Only the POST decides whether
a borehole counts as delivered.
"""

import logging
import re
from typing import Any

import requests

from .schema import Borehole

log = logging.getLogger("bem")

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def document_id_from_stem(stem: str) -> str | None:
    """`mix documents.backfill` stores files as <document_id><ext> (ADR-0014): the stem is the ID."""
    return stem.lower() if UUID_RE.fullmatch(stem) else None


def to_create_request(borehole: Borehole, document_id: str | None) -> dict[str, Any]:
    """The POST /api/boreholes body: {"borehole": {...}, "layers": [...], "document_id": ...}."""
    data = borehole.to_api_dict()
    layers = data.pop("borehole_layers")
    body: dict[str, Any] = {"borehole": data, "layers": layers}
    if document_id:
        body["document_id"] = document_id
    return body


class ApiClient:
    """Thin client for the pipeline endpoints. `base_url` is e.g. http://localhost:4000/api."""

    def __init__(self, base_url: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _put(self, path: str, body: dict[str, Any]) -> None:
        """Tracking call: log a failure, never raise."""
        try:
            requests.put(f"{self.base_url}{path}", json=body, timeout=self.timeout).raise_for_status()
        except requests.RequestException as e:
            log.warning("API tracking call failed (PUT %s): %s", path, e)

    def put_stage(self, document_id: str, stage: str, output: dict[str, Any], error: str | None = None) -> None:
        status = "error" if error else "ok"
        self._put(f"/documents/{document_id}/pipeline_stages/{stage}", {"status": status, "output": output, "error": error})

    def set_status(self, document_id: str, status: str) -> None:
        """Document status shown in the UI: `extracted` or `failed` once the pipeline is done."""
        self._put(f"/documents/{document_id}/status", {"status": status})

    def put_triage_sections(self, document_id: str, sections: list[Borehole]) -> None:
        body = [
            {
                "section_index": i,
                "borehole_id_guess": s.external_id,
                "raw_markdown": s.raw_markdown,
                "translate_errors": s.translate_errors,
            }
            for i, s in enumerate(sections)
        ]
        self._put(f"/documents/{document_id}/triage_sections", {"sections": body})

    def put_extraction_result(self, document_id: str, index: int, record: Borehole | None, error: str | None = None) -> None:
        body = {
            "status": "error" if error else "ok",
            "extracted_fields": record.to_api_dict() if record else None,
            "validation_issues": {},
            "error": error,
        }
        self._put(f"/documents/{document_id}/triage_sections/{index}/extraction_result", body)

    def put_sink_result(self, document_id: str, index: int, body: dict[str, Any]) -> None:
        self._put(f"/documents/{document_id}/triage_sections/{index}/sink_result", {"target": "api", **body})

    def post_borehole(self, borehole: Borehole, document_id: str | None) -> dict[str, Any]:
        """Create the borehole. Raises requests.HTTPError on a non-2xx response (the body is in the message)."""
        resp = requests.post(f"{self.base_url}/boreholes", json=to_create_request(borehole, document_id), timeout=self.timeout)
        if not resp.ok:
            raise requests.HTTPError(f"{resp.status_code} {resp.text}", response=resp)
        return resp.json()
