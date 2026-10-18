"""HTTP server for the pipeline: the API starts a run with `POST /execute` (ADR-0033, ADR-0035).

Run with: uv run python -m pipeline.server   (env: BEM_API_URL, BEM_PORT, BEM_WORKDIR)

`/execute` receives a document id, the API's `pipeline_runs.id` (as `pipeline_id`) and a config, queues
the run and answers 202 at once. One worker thread downloads the document from the API
(`GET /documents/:id/file`) when it starts stage 1 and runs the pipeline. Every stage is tracked
as an exec_stage (ADR-0040): filter/split are created `new` up front, extract/transform per borehole
once split has found them; each turns `running` when it starts and `success`/`failed`/`stopped`
with its result, error, model, effort and usage. A transform stage only succeeds once its borehole
is stored (`POST /boreholes`). Finally the run gets `PUT /pipeline_runs/:id/status`
(`completed`/`failed`/`stopped`, with the error). `POST /runs/:id/stop` cancels a queued or
running run.
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
from dataclasses import dataclass, field

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .__main__ import run_pipeline
from .ai import StepReport, Timer
from .config import PipelineConfig
from .ai import PipelineError, PipelineStopped, get_ai, log
from .api_service import ApiError, ApiService
from .din4023 import Din4023Error
from .output import Recorder, Tracker, persist_enabled
from .naming import new_run, run_id
from .steps.extract import extract_boreholes
from .steps.translate import transform_boreholes

WORKDIR = pathlib.Path(os.environ.get("BEM_WORKDIR", pathlib.Path(__file__).resolve().parent.parent / "out" / "server"))
CHUNK_SIZE = int(os.environ.get("BEM_CHUNK_SIZE", "10"))
WORKERS = int(os.environ.get("BEM_WORKERS", "4"))


@dataclass
class Job:
    document_id: str
    pipeline_id: str | None
    config: PipelineConfig
    stop: threading.Event = field(default_factory=threading.Event)
    # (stage, position) when only one failed/stopped extract or transform job of the run is redone
    retry: tuple[str, int] | None = None


_jobs: queue.Queue[Job] = queue.Queue()
_active: dict[str, Job] = {}  # pipeline_id -> queued or running job, for /runs/:id/stop
_active_lock = threading.Lock()


def _safe_name(text: str) -> str:
    return re.sub(r"[^\w.-]+", "_", text).strip("_") or "borehole"


def _error_text(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"[:4000]


class RunTracker(Tracker):
    """Reports the lifecycle of every stage of one run to the API as exec_stages (ADR-0040).

    Split-out PDFs are uploaded as documents of their own and linked to their extract/transform
    stages; a finished transform stores its borehole before the stage counts as `success`.
    """

    def __init__(self, api: ApiService, run: str, document_id: str):
        self.api = api
        self.run = run
        self.document_id = document_id
        self.split_documents: dict[int, str] = {}  # borehole position -> id of its split-out PDF document
        self.boreholes: dict[int, str] = {}  # position -> id of the stored borehole
        self.upload_errors: list[str] = []
        self._ids: dict[tuple[str, int | None], str] = {}  # (stage, position) -> exec_stage id
        self._lock = threading.Lock()  # extract/transform report from parallel threads

    def _documents(self, position: int | None) -> list[str]:
        # extract/transform link to the source and the split PDF they read
        return [self.document_id] + ([self.split_documents[position]] if position in self.split_documents else [])

    def _create(self, stage: str, position: int | None, status: str, **fields) -> None:
        row = self.api.create_exec_stage(stage, self.run, self._documents(position), position, status=status, **fields)
        with self._lock:
            self._ids[(stage, position)] = row["id"]

    def _update(self, stage: str, position: int | None, status: str, **fields) -> None:
        with self._lock:
            stage_id = self._ids.get((stage, position))
        if stage_id is None:  # never planned, or creating it failed: record it now
            self._create(stage, position, status, **fields)
        else:
            self.api.update_exec_stage(stage_id, status, **fields)

    def plan(self) -> None:
        """Create the whole-document stages as `new`, so the run shows what is still to come."""
        for stage in ("filter", "split"):
            try:
                self._create(stage, None, "new")
            except ApiError as e:
                log(f"{self.document_id}: {stage} stage not created: {e}")

    def started(self, stage: str, position: int | None, model: str, effort: str) -> None:
        self._update(stage, position, "running", model=model, effort=effort)

    def succeeded(self, stage, position, data, files, usage) -> None:
        if stage == "split":
            self._upload_split(data, files)
        if stage == "transform":
            try:
                data = data | {"borehole_id": self._store_borehole(position, data["payload"])}
            except (ApiError, Din4023Error) as e:
                self.upload_errors.append(f"borehole {position}: {e}")
                self._update(stage, position, "failed", data=data, usage=usage, error=f"upload: {_error_text(e)}")
                return
        extra = list(self.split_documents.values()) if stage == "split" else None
        self._update(stage, position, "success", data=data, usage=usage, document_ids=extra)
        if stage == "split":
            for position in range(1, len(data["boreholes"]) + 1):  # what extract/transform will do
                for later in ("extract", "transform"):
                    try:
                        self._create(later, position, "new")
                    except ApiError as e:
                        log(f"{self.document_id}: {later} #{position} stage not created: {e}")

    def failed(self, stage, position, error, usage) -> None:
        status = "stopped" if isinstance(error, PipelineStopped) else "failed"
        self._update(stage, position, status, usage=usage, error=_error_text(error))

    def _upload_split(self, data: dict, files: list[pathlib.Path]) -> None:
        # each split-out PDF becomes a document of its own; the grouping records its id
        for i, (group, f) in enumerate(zip(data["boreholes"], files), 1):
            try:
                name = f"{self.document_id[:8]}_{_safe_name(group['label'])}.pdf"
                self.split_documents[i] = group["document_id"] = self.api.upload_document(f, name)
            except ApiError as e:
                log(f"{self.document_id}: split document {i} not uploaded: {e}")

    def _store_borehole(self, position: int, payload: dict) -> str:
        # the source stays the original; the split-out PDF this borehole came from is linked as additional
        additional = [self.split_documents[position]] if position in self.split_documents else []
        stored = self.api.upload_borehole(payload, self.document_id, additional)
        borehole_id = stored.get("data", {}).get("id")
        self.boreholes[position] = borehole_id
        return borehole_id


def process(job: Job, api: ApiService) -> tuple[str, str | None]:
    """Download one document, run the pipeline on it and upload everything.

    Returns the run's final status (`completed`/`failed`/`stopped`) and, unless completed, why.
    """
    new_run()
    # exec_stages and the report are grouped by the API's pipeline run id, which GET /pipeline_runs/:id filters on
    run = job.pipeline_id or run_id()
    document_id = job.document_id
    out_dir = WORKDIR / document_id / "out"
    get_ai().debug_dir = out_dir / "debug" if persist_enabled() else None
    tracker = RunTracker(api, run, document_id)
    tracker.plan()

    reports = []
    try:
        with tempfile.TemporaryDirectory(prefix="bem-") as tmp:
            # the download is a scratch copy; prod keeps no local copy of the confidential document
            try:
                pdf = api.download_document(document_id, pathlib.Path(tmp) / f"{document_id}.pdf")
            except ApiError as e:
                Recorder(tracker).record_failure("filter", e)
                return "failed", f"download failed: {e}"
            results, reports, _ = run_pipeline(pdf, out_dir, CHUNK_SIZE, WORKERS, job.config, tracker, job.stop)
    except PipelineStopped:
        return "stopped", "stopped by user"
    except PipelineError as e:
        return "failed", str(e)[:4000]
    finally:
        if reports:
            try:
                api.upload_report(document_id, run, [r.to_dict() for r in reports])
            except ApiError as e:
                log(f"{document_id}: report not uploaded: {e}")

    if not results:
        return "failed", "no borehole log pages found"
    if tracker.upload_errors:
        return "failed", f"{len(tracker.upload_errors)} of {len(results)} borehole(s) not stored: " + "; ".join(
            tracker.upload_errors
        )[:4000]
    return "completed", None


def _latest_rows(run: dict) -> dict[tuple[str, int | None], dict]:
    """The newest exec_stage per (type, position); the API lists them newest first."""
    latest: dict[tuple[str, int | None], dict] = {}
    for row in run.get("exec_stages") or []:
        latest.setdefault((row["type"], row.get("position")), row)
    return latest


def process_retry(job: Job, api: ApiService) -> tuple[str, str | None]:
    """Redo one extract or transform job of a finished run as a new exec_stage.

    Extract is followed by transform for the same borehole. Inputs come from the run's earlier
    stages: the split-out PDF (extract) or the stored extraction result (transform). Returns the
    whole run's final status, judged from the newest row of every extract/transform job.
    """
    stage, position = job.retry
    new_run()
    run_id_ = job.pipeline_id
    document_id = job.document_id
    c = job.config
    try:
        run = api.get_pipeline_run(run_id_)
    except ApiError as e:
        return "failed", f"could not load the run: {e}"
    latest = _latest_rows(run)
    split = latest.get(("split", None))
    boreholes = ((split or {}).get("data") or {}).get("boreholes") or []
    if split is None or split.get("status") != "success" or not 1 <= position <= len(boreholes):
        return "failed", f"cannot retry {stage} #{position}: the split result is missing"

    tracker = RunTracker(api, run_id_, document_id)
    tracker.split_documents = {i: b["document_id"] for i, b in enumerate(boreholes, 1) if b.get("document_id")}
    for (type_, pos), row in latest.items():  # keep the borehole ids of jobs that already stored theirs
        if type_ == "transform" and row.get("status") == "success" and pos is not None:
            tracker.boreholes[pos] = (row.get("data") or {}).get("borehole_id")
    recorder = Recorder(tracker)
    label = _safe_name(boreholes[position - 1].get("label") or f"borehole_{position}")
    out_dir = WORKDIR / document_id / "out"
    get_ai().debug_dir = out_dir / "debug" if persist_enabled() else None
    r3 = StepReport("3 extract", c.extract.model, c.extract.effort, stop=job.stop)
    r4 = StepReport("4 transform to db", c.transform.model, c.transform.effort, stop=job.stop)

    try:
        with tempfile.TemporaryDirectory(prefix="bem-") as tmp:
            if not persist_enabled():
                out_dir = pathlib.Path(tmp)
            pdf = out_dir / "retry" / f"{label}.pdf"
            if stage == "extract":
                split_document = tracker.split_documents.get(position)
                if split_document is None:
                    return "failed", f"cannot retry extract #{position}: its split-out PDF is missing"
                api.download_document(split_document, pdf)
                with Timer(r3):
                    (_, data), = extract_boreholes([pdf], out_dir, r3, 1, recorder, position)
            else:
                extract_row = latest.get(("extract", position)) or {}
                data = extract_row.get("data")
                if data is None or extract_row.get("status") != "success":
                    return "failed", f"cannot retry transform #{position}: its extraction result is missing"
            with Timer(r4):
                transform_boreholes([(pdf, data)], out_dir, r4, 1, recorder, position)
    except PipelineStopped:
        return "stopped", "stopped by user"
    except (PipelineError, ApiError) as e:
        log(f"{document_id}: retry of {stage} #{position} failed: {e}")  # recorded on the job itself
    if tracker.upload_errors:
        log(f"{document_id}: {'; '.join(tracker.upload_errors)}")

    try:  # the other jobs keep their results, so judge the run by the newest row of every job
        latest = _latest_rows(api.get_pipeline_run(run_id_))
    except ApiError as e:
        return "failed", f"could not reload the run: {e}"
    bad = sorted(
        f"{t} #{p}" for (t, p), row in latest.items() if t in ("extract", "transform") and row.get("status") != "success"
    )
    # planned rows that never ran (`new`) belong to boreholes whose extract failed
    return ("failed", f"{len(bad)} job(s) not successful: {', '.join(bad)}"[:4000]) if bad else ("completed", None)


def _worker() -> None:
    api = ApiService()
    while True:
        job = _jobs.get()
        document_id, pipeline_id = job.document_id, job.pipeline_id
        try:
            if job.stop.is_set():  # stopped while queued; the API has already marked it stopped
                log(f"{document_id}: pipeline {pipeline_id} stopped before it started")
                continue
            if job.retry:
                log(f"{document_id}: pipeline {pipeline_id} retries {job.retry[0]} #{job.retry[1]}")
            else:
                log(f"{document_id}: pipeline {pipeline_id or '-'} starts with stage 1 (filter)")
            try:
                status, error = process_retry(job, api) if job.retry else process(job, api)
            except Exception as e:  # keep the worker alive whatever one document does
                log(f"{document_id}: unexpected error")
                traceback.print_exc()
                status, error = "failed", f"unexpected error: {_error_text(e)}"
            log(f"{document_id}: pipeline {pipeline_id or '-'} {status}" + (f": {error}" if error else ""))
            if pipeline_id is None:
                log(f"{document_id}: no pipeline_id given, cannot report status {status!r}")
                continue
            try:
                api.set_pipeline_run_status(pipeline_id, status, error)
            except ApiError as e:
                log(f"{document_id}: could not set pipeline run status: {e}")
        finally:
            if pipeline_id is not None:
                with _active_lock:
                    _active.pop(pipeline_id, None)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if shutil.which("pdftoppm") is None:
        log("WARNING: pdftoppm (poppler) not found, scanned pages cannot be read")
    threading.Thread(target=_worker, daemon=True, name="pipeline-worker").start()
    yield


app = FastAPI(title="bem pipeline", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    with _active_lock:
        active = list(_active)
    return {"status": "ok", "queued": _jobs.qsize(), "active_runs": active}


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
    job = Job(document_id, request.pipeline_id, request.config)
    if job.pipeline_id is not None:
        with _active_lock:
            _active[job.pipeline_id] = job
    _jobs.put(job)
    return {
        "document_id": document_id,
        "pipeline_id": request.pipeline_id,
        "status": "queued",
        "config": request.config.model_dump(),
    }


class RetryRequest(BaseModel):
    document_id: uuid.UUID
    stage: Literal["extract", "transform"]
    position: int = Field(ge=1)  # 1-based borehole index within the run
    config: PipelineConfig = PipelineConfig()


@app.post("/runs/{pipeline_id}/retry", status_code=202)
def retry(pipeline_id: str, request: RetryRequest) -> dict:
    """Queue the redo of one failed or stopped extract/transform job of an existing run (called by
    the API's `POST /exec_stages/:id/retry`). The attempt is recorded as a new exec_stage; extract
    is followed by transform for that borehole."""
    with _active_lock:
        if pipeline_id in _active:
            raise HTTPException(409, f"run {pipeline_id} is still queued or running")
        job = Job(str(request.document_id), pipeline_id, request.config, retry=(request.stage, request.position))
        _active[pipeline_id] = job
    _jobs.put(job)
    return {"pipeline_id": pipeline_id, "stage": request.stage, "position": request.position, "status": "queued"}


@app.post("/runs/{pipeline_id}/stop", status_code=202)
def stop(pipeline_id: str) -> dict:
    """Cancel a queued or running run (called by the API's `POST /pipeline_runs/:id/stop`).

    A running run ends at its next stage, borehole or AI call; calls already in flight finish first.
    """
    with _active_lock:
        job = _active.get(pipeline_id)
    if job is None:
        raise HTTPException(404, f"no queued or running run {pipeline_id}")
    job.stop.set()
    return {"pipeline_id": pipeline_id, "status": "stopping"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("BEM_PORT", "8000")))


if __name__ == "__main__":
    main()
