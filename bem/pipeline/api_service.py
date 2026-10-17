"""Client for the Elixir API: document download, stage tracking, report and borehole upload (ADR-0034, ADR-0031).

The base URL comes from `BEM_API_URL` (environment or `bem/.env`, see pipeline/__init__.py; default
http://localhost:4000); `/api` is appended if missing.
"""

import os
import pathlib
from urllib.parse import urlparse

import httpx

from . import din4023


class ApiError(RuntimeError):
    pass


def api_base_url(url: str | None = None) -> str:
    url = (url or os.environ.get("BEM_API_URL") or "http://localhost:4000").strip().rstrip("/")
    if "://" not in url:
        url = f"http://{url}"
    return url if urlparse(url).path.strip("/") else f"{url}/api"


class ApiService:
    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None):
        self.base_url = api_base_url(base_url)
        self._client = client or httpx.Client(timeout=60)

    def _send(self, method: str, path: str, body: dict) -> dict:
        try:
            r = self._client.request(method, f"{self.base_url}{path}", json=body)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ApiError(f"{method} {path} -> {e.response.status_code}: {e.response.text[:500]}") from e
        except httpx.HTTPError as e:
            raise ApiError(f"{method} {path} failed: {e}") from e
        return r.json() if r.content else {}

    def create_exec_stage(
        self, stage: str, run_id: str, data: dict, document_ids: list[str], position: int | None = None
    ) -> dict:
        """`POST /exec_stages`: `stage` is filter|split|extract|transform; `position` is the 1-based
        borehole index for extract/transform."""
        return self._send(
            "POST",
            "/exec_stages",
            {"type": stage, "run_id": run_id, "position": position, "data": data, "document_ids": document_ids},
        )

    def upload_report(self, document_id: str, run_id: str, steps: list[dict]) -> dict:
        """`POST /reports`: the run's per-step model/time/token/cost stats (`data` must be an object)."""
        return self._send("POST", "/reports", {"document_id": document_id, "run_id": run_id, "data": {"steps": steps}})

    def upload_borehole(self, payload: dict, document_id: str) -> dict:
        """`POST /boreholes`. The payload must satisfy DIN 4023 (see `din4023.conform`), otherwise
        `Din4023Error` is raised and nothing is sent."""
        conformed, issues = din4023.conform(payload)
        if issues:
            raise din4023.Din4023Error(issues)
        return self._send(
            "POST",
            "/boreholes",
            {"borehole": conformed["borehole"], "layers": conformed["layers"], "document_id": document_id},
        )

    def download_document(self, document_id: str, dest: pathlib.Path) -> pathlib.Path:
        """`GET /documents/:id/file`: stream the stored PDF to `dest`. Raises ApiError if it is missing
        or not a PDF."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        path = f"/documents/{document_id}/file"
        try:
            with self._client.stream("GET", f"{self.base_url}{path}") as r:
                r.raise_for_status()
                with dest.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        except httpx.HTTPStatusError as e:
            raise ApiError(f"GET {path} -> {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise ApiError(f"GET {path} failed: {e}") from e
        with dest.open("rb") as f:
            if f.read(5) != b"%PDF-":
                dest.unlink(missing_ok=True)
                raise ApiError(f"document {document_id} is not a PDF, only PDFs are supported")
        return dest

    def set_pipeline_run_status(self, pipeline_id: str, status: str) -> dict:
        """`PUT /pipeline_runs/:id/status`: `completed` or `failed` (ADR-0035). `pipeline_id` is the
        `pipeline_runs.id` the API gave `/execute` back as `pipeline_id`."""
        return self._send("PUT", f"/pipeline_runs/{pipeline_id}/status", {"status": status})
