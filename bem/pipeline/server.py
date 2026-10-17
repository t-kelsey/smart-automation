"""HTTP server for the pipeline: the API starts a run with `POST /execute` (ADR-0033, ADR-0035).

Run with: uv run python -m pipeline.server   (env: BEM_API_URL, BEM_PORT, BEM_WORKDIR)

`/execute` receives a document id, the API's `pipeline_runs.id` (as `pipeline_id`) and a config, queues
the run and answers 202 at once. One worker thread downloads the document from the API
(`GET /documents/:id/file`) when it starts stage 1, runs the pipeline and reports back to the API:
`POST /boreholes` per borehole (linked to the document), then `PUT /pipeline_runs/:id/status` with
`completed` or `failed`.
"""

import os
import pathlib
import queue
import re
import shutil
import tempfile
import threading
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from .__main__ import run_pipeline
from .config import PipelineConfig
from .ai import PipelineError, get_ai, log
from .api_service import ApiError, ApiService
from .din4023 import Din4023Error
from .output import persist_enabled
from .naming import new_run, run_id

WORKDIR = pathlib.Path(os.environ.get("BEM_WORKDIR", pathlib.Path(__file__).resolve().parent.parent / "out" / "server"))
CHUNK_SIZE = int(os.environ.get("BEM_CHUNK_SIZE", "10"))
WORKERS = int(os.environ.get("BEM_WORKERS", "4"))

_jobs: queue.Queue[tuple[str, str | None, PipelineConfig]] = queue.Queue()


def _safe_name(text: str) -> str:
    return re.sub(r"[^\w.-]+", "_", text).strip("_") or "borehole"


def process(document_id: str, pipeline_id: str | None, config: PipelineConfig, api: ApiService) -> bool:
    """Download one document, run the pipeline on it and upload everything. Returns success."""
    new_run()
    # exec_stages and the report are grouped by the API's pipeline run id, which GET /pipeline_runs/:id filters on
    run = pipeline_id or run_id()
    out_dir = WORKDIR / document_id / "out"
    get_ai().debug_dir = out_dir / "debug" if persist_enabled() else None

    split_documents: dict[int, str] = {}  # borehole position -> id of its split-out PDF document

    def on_stage(stage: str, position: int | None, data: dict, files: list[pathlib.Path]) -> None:
        if stage == "split":
            # each split-out PDF becomes a document of its own; the grouping records its id
            for i, (group, f) in enumerate(zip(data["boreholes"], files), 1):
                try:
                    name = f"{document_id[:8]}_{_safe_name(group['label'])}.pdf"
                    split_documents[i] = group["document_id"] = api.upload_document(f, name)
                except ApiError as e:
                    log(f"{document_id}: split document {i} not uploaded: {e}")
        document_ids = [document_id]
        if stage == "split":
            document_ids += split_documents.values()
        elif position in split_documents:  # extract/transform link to the source and their split PDF
            document_ids.append(split_documents[position])
        api.create_exec_stage(stage, run, data, document_ids, position)

    with tempfile.TemporaryDirectory(prefix="bem-") as tmp:
        # the download is a scratch copy; prod keeps no local copy of the confidential document
        try:
            pdf = api.download_document(document_id, pathlib.Path(tmp) / f"{document_id}.pdf")
        except ApiError as e:
            log(f"{document_id}: download failed: {e}")
            return False
        try:
            results, reports, _ = run_pipeline(pdf, out_dir, CHUNK_SIZE, WORKERS, config, on_stage)
        except PipelineError as e:
            log(f"{document_id}: pipeline failed: {e}")
            return False
    try:
        api.upload_report(document_id, run, [r.to_dict() for r in reports])
    except ApiError as e:
        log(f"{document_id}: report not uploaded: {e}")
    if not results:
        log(f"{document_id}: no boreholes found")
        return False

    ok = True
    for position, r in enumerate(results, 1):  # same order as the extract/transform positions
        name = r["payload"]["borehole"].get("name")
        # the source stays the original; the split-out PDF this borehole came from is linked as additional
        additional = [split_documents[position]] if position in split_documents else []
        try:
            api.upload_borehole(r["payload"], document_id, additional)
        except Din4023Error as e:
            log(f"{document_id}: borehole {name!r} violates DIN 4023, not uploaded: {e}")
            ok = False
        except ApiError as e:
            log(f"{document_id}: borehole {name!r} not uploaded: {e}")
            ok = False
    return ok


def _worker() -> None:
    api = ApiService()
    while True:
        document_id, pipeline_id, config = _jobs.get()
        log(f"{document_id}: pipeline {pipeline_id or '-'} starts with stage 1 (filter)")
        try:
            success = process(document_id, pipeline_id, config, api)
        except Exception:  # keep the worker alive whatever one document does
            log(f"{document_id}: unexpected error")
            traceback.print_exc()
            success = False
        status = "completed" if success else "failed"
        if pipeline_id is None:
            log(f"{document_id}: no pipeline_id given, cannot report status {status!r}")
            continue
        try:
            api.set_pipeline_run_status(pipeline_id, status)
        except ApiError as e:
            log(f"{document_id}: could not set pipeline run status: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if shutil.which("pdftoppm") is None:
        log("WARNING: pdftoppm (poppler) not found, scanned pages cannot be read")
    threading.Thread(target=_worker, daemon=True, name="pipeline-worker").start()
    yield


app = FastAPI(title="bem pipeline", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "queued": _jobs.qsize()}


class ExecuteRequest(BaseModel):
    document_id: uuid.UUID
    # The API's `pipeline_runs.id` (ADR-0035): echoed back, used for `PUT /pipeline_runs/:id/status`
    # on completion. Optional only so /execute can be called directly without a pipeline_runs row
    # (e.g. manual testing) — then completion status cannot be reported anywhere.
    pipeline_id: str | None = None
    config: PipelineConfig = PipelineConfig()  # per step `filter|split|extract|transform`: model + effort


@app.post("/execute", status_code=202)
def execute(request: ExecuteRequest) -> dict:
    """Queue a run for an existing document. Stage 1 (filter) starts by downloading it from the API.

    JSON body: `{"document_id": "<uuid>", "config": {"filter": {"model": "haiku", "effort": "high"}, ...}}`;
    omitted steps use their defaults.
    """
    document_id = str(request.document_id)
    _jobs.put((document_id, request.pipeline_id, request.config))
    return {
        "document_id": document_id,
        "pipeline_id": request.pipeline_id,
        "status": "queued",
        "config": request.config.model_dump(),
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("BEM_PORT", "8000")))


if __name__ == "__main__":
    main()
