"""Client for the Elixir API: document download, stage tracking, report and borehole upload (ADR-0034, ADR-0040).

The base URL comes from `BEM_API_URL` (environment or `bem/.env`, see pipeline/__init__.py; default
http://localhost:4000); `/api` is appended if missing.
"""

import os
import pathlib
from urllib.parse import urlparse

import httpx

from . import din4023, pdfutil


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

    def get_pipeline_run(self, pipeline_id: str) -> dict:
        """`GET /pipeline_runs/:id`: the run with its `exec_stages` (newest first, `data` included)."""
        path = f"/pipeline_runs/{pipeline_id}"
        try:
            r = self._client.get(f"{self.base_url}{path}")
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ApiError(f"GET {path} -> {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise ApiError(f"GET {path} failed: {e}") from e
        return r.json()["data"]

    def create_exec_stage(
        self,
        stage: str,
        run_id: str,
        document_ids: list[str],
        position: int | None = None,
        *,
        status: str = "new",
        **fields,
    ) -> dict:
        """`POST /exec_stages`: `stage` is filter|split|extract|transform; `position` is the 1-based
        borehole index for extract/transform; `status` new|running|success|failed|stopped (ADR-0040).
        `fields`: optional `data`, `error`, `model`, `effort`, `usage`. Returns the created stage."""
        body = {"type": stage, "run_id": run_id, "position": position, "status": status, "document_ids": document_ids}
        return self._send("POST", "/exec_stages", body | _present(fields))["data"]

    def update_exec_stage(self, stage_id: str, status: str, **fields) -> dict:
        """`PUT /exec_stages/:id`: report progress (`running`, then `success`/`failed`/`stopped`).
        `fields`: optional `data`, `error`, `model`, `effort`, `usage`, `document_ids` (linked in
        addition). The API stamps `started_at`/`finished_at`. Returns the updated stage."""
        return self._send("PUT", f"/exec_stages/{stage_id}", {"status": status} | _present(fields))["data"]

    def upload_report(self, document_id: str, run_id: str, steps: list[dict]) -> dict:
        """`POST /reports`: the run's per-step model/time/token/cost stats (`data` must be an object)."""
        return self._send("POST", "/reports", {"document_id": document_id, "run_id": run_id, "data": {"steps": steps}})

    def upload_borehole(self, payload: dict, document_id: str, additional_document_ids: list[str] | None = None) -> dict:
        """`POST /boreholes`. The payload must satisfy DIN 4023 (see `din4023.conform`), otherwise
        `Din4023Error` is raised and nothing is sent. `document_id` becomes the borehole's original document,
        `additional_document_ids` (e.g. its split-out PDF) are linked as additional documents."""
        conformed, issues = din4023.conform(payload)
        if issues:
            raise din4023.Din4023Error(issues)
        return self._send(
            "POST",
            "/boreholes",
            {
                "borehole": conformed["borehole"],
                "layers": conformed["layers"],
                "document_id": document_id,
                "additional_document_ids": additional_document_ids or [],
            },
        )

    def download_document(self, document_id: str, dest: pathlib.Path) -> pathlib.Path:
        """`GET /documents/:id/file`: stream the stored file to `dest` as a PDF (Word documents and images are converted).
        Raises ApiError if it is missing or cannot be converted."""
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
            if f.read(5) == b"%PDF-":
                return dest
        # not a PDF: the pipeline reads PDFs only, so Word documents and images are converted
        converted = dest.with_name(dest.name + ".converted.pdf")
        try:
            if pdfutil.is_docx(dest):
                pdfutil.docx_to_pdf(dest, converted)
            else:
                pdfutil.image_to_pdf(dest, converted)
        except ValueError as e:
            raise ApiError(f"document {document_id} could not be converted to PDF: {e}") from e
        finally:
            dest.unlink(missing_ok=True)
        converted.rename(dest)
        return dest

    def upload_document(self, path: pathlib.Path, filename: str) -> str:
        """`POST /documents` (multipart `file`): store a file, e.g. a split-out borehole PDF, as a new
        document and return its id."""
        try:
            with path.open("rb") as f:
                r = self._client.post(f"{self.base_url}/documents", files={"file": (filename, f, "application/pdf")})
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ApiError(f"POST /documents -> {e.response.status_code}: {e.response.text[:500]}") from e
        except httpx.HTTPError as e:
            raise ApiError(f"POST /documents failed: {e}") from e
        return r.json()["data"]["id"]

    def set_pipeline_run_status(self, pipeline_id: str, status: str, error: str | None = None) -> dict:
        """`PUT /pipeline_runs/:id/status`: `completed`, `failed` (with `error`) or `stopped`
        (ADR-0035, ADR-0040). `pipeline_id` is the `pipeline_runs.id` the API gave `/execute`. The API
        answers 409 if the run already ended otherwise (e.g. it was stopped meanwhile)."""
        return self._send("PUT", f"/pipeline_runs/{pipeline_id}/status", {"status": status} | _present({"error": error}))


def _present(fields: dict) -> dict:
    return {k: v for k, v in fields.items() if v is not None}
