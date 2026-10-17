"""HTTP endpoint of the pipeline (ADR-0033): the API posts every uploaded document here.

    bem-serve [--host 0.0.0.0] [--port 8000]      # or: python -m bem.server

POST /process (multipart/form-data: `file` named <document_id><ext>, `document_id`) answers
`202` at once. The file is then run through the pipeline in a background worker, one at a time
(OCR and the model are heavy), and the stage results and boreholes are reported to the API
(`BEM_API_URL`) exactly as `bem --to api` does.
"""

import argparse
import logging
import os
import queue
import shutil
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
import uvicorn

from bem.api import ApiClient, UUID_RE
from bem.main import SUPPORTED_SUFFIXES, process_file
from bem.output import make_sink

log = logging.getLogger("bem")

app = FastAPI(title="bem pipeline")
jobs: queue.Queue[tuple[Path, str]] = queue.Queue()
work_dir = Path(os.environ.get("BEM_WORK_DIR", tempfile.gettempdir())) / "bem-uploads"


def run_job(path: Path, document_id: str) -> None:
    client = ApiClient(os.environ.get("BEM_API_URL", "http://localhost:4000/api"))
    try:
        with make_sink("api", client=client, out_dir=Path("out")) as sink:
            count = process_file(path, sink, debug=False, client=client)
        log.info("%s: %d borehole(s)", path.name, count)
    except Exception:
        log.exception("failed: %s", path.name)
        client.set_status(document_id, "failed")
    else:
        client.set_status(document_id, "extracted")
    finally:
        path.unlink(missing_ok=True)


def worker() -> None:
    while True:
        path, document_id = jobs.get()
        try:
            run_job(path, document_id)
        finally:
            jobs.task_done()


@app.post("/process", status_code=202)
def process(file: UploadFile = File(...), document_id: str = Form(...)) -> dict:
    if not UUID_RE.fullmatch(document_id):
        raise HTTPException(422, "document_id must be a UUID")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(422, f"unsupported file type {suffix!r}")
    work_dir.mkdir(parents=True, exist_ok=True)
    # <document_id><ext>: process_file takes the document ID from the file stem (ADR-0014)
    path = work_dir / f"{document_id.lower()}{suffix}"
    with path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    jobs.put((path, document_id.lower()))
    return {"document_id": document_id.lower(), "queued": jobs.qsize()}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def start_worker() -> None:
    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BEM_PORT", "8000")))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
