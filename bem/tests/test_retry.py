"""Run from bem/: uv run python -m unittest discover tests"""

import pathlib
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pipeline import server
from pipeline.config import PipelineConfig

DOC = "00000000-0000-0000-0000-000000000001"
SPLIT_DOC = "00000000-0000-0000-0000-000000000002"


def row(type_, position, status, data=None):
    return {"id": f"{type_}{position}{status}", "type": type_, "position": position, "status": status, "data": data}


class FakeApi:
    """Newest-first exec_stages like the real API; created rows are prepended."""

    def __init__(self, stages):
        self.stages = stages
        self.created = []
        self.downloads = []
        self.final_status = None

    def get_pipeline_run(self, pipeline_id):
        return {"id": pipeline_id, "exec_stages": list(self.stages)}

    def download_document(self, document_id, dest):
        self.downloads.append(document_id)
        return dest

    def create_exec_stage(self, stage, run_id, document_ids, position=None, *, status="new", **fields):
        self.created.append((stage, position, status, document_ids))
        new = row(stage, position, status, fields.get("data"))
        self.stages.insert(0, new)
        return {"id": new["id"]}

    def update_exec_stage(self, stage_id, status, **fields):
        for r in self.stages:
            if r["id"] == stage_id:
                r["status"] = status
                if "data" in fields:
                    r["data"] = fields["data"]
        return {}


SPLIT = row("split", None, "success", {"boreholes": [{"label": "BH1", "document_id": SPLIT_DOC}]})


class ProcessRetry(unittest.TestCase):
    def job(self, stage, position=1):
        return server.Job(DOC, "run-1", PipelineConfig(), retry=(stage, position))

    def test_transform_retry_uses_stored_extraction_and_completes_the_run(self):
        api = FakeApi([row("transform", 1, "failed"), row("extract", 1, "success", {"x": 1}), SPLIT])
        seen = {}

        def fake_transform(extracted, out_dir, report, workers, recorder, first_position):
            seen["data"], seen["position"] = extracted[0][1], first_position
            recorder.start("transform", report, position=first_position)
            recorder.record("transform", {"payload": {}}, report=report, position=first_position)
            return []

        with mock.patch.object(server, "transform_boreholes", fake_transform), mock.patch.object(
            server.RunTracker, "_store_borehole", return_value="b1"
        ):
            status, error = server.process_retry(self.job("transform"), api)

        self.assertEqual((status, error), ("completed", None))
        self.assertEqual(seen, {"data": {"x": 1}, "position": 1})
        self.assertEqual(api.downloads, [])
        # the new attempt is a new row linked to the source and split documents
        self.assertEqual(api.created[0], ("transform", 1, "running", [DOC, SPLIT_DOC]))

    def test_extract_retry_downloads_split_pdf_and_failure_keeps_run_failed(self):
        api = FakeApi([row("extract", 1, "failed"), SPLIT])

        def fake_extract(files, out_dir, report, workers, recorder, first_position):
            self.assertEqual(files[0].name, "BH1.pdf")
            recorder.start("extract", report, position=first_position)
            raise server.PipelineError("model said no")

        with mock.patch.object(server, "extract_boreholes", fake_extract):
            status, error = server.process_retry(self.job("extract"), api)

        self.assertEqual(api.downloads, [SPLIT_DOC])
        self.assertEqual(status, "failed")
        self.assertIn("extract #1", error)

    def test_other_failed_jobs_keep_the_run_failed(self):
        api = FakeApi(
            [row("transform", 1, "failed"), row("extract", 2, "failed"), row("extract", 1, "success", {}), SPLIT]
        )

        def fake_transform(extracted, out_dir, report, workers, recorder, first_position):
            recorder.start("transform", report, position=first_position)
            recorder.record("transform", {"payload": {}}, report=report, position=first_position)

        with mock.patch.object(server, "transform_boreholes", fake_transform), mock.patch.object(
            server.RunTracker, "_store_borehole", return_value="b1"
        ):
            status, error = server.process_retry(self.job("transform"), api)

        self.assertEqual(status, "failed")
        self.assertEqual(error, "1 job(s) not successful: extract #2")

    def test_missing_split_result_fails_without_running_anything(self):
        status, error = server.process_retry(self.job("extract"), FakeApi([row("filter", None, "success")]))
        self.assertEqual(status, "failed")
        self.assertIn("split result is missing", error)


class RetryEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)  # no lifespan: no worker thread, jobs stay queued
        server._active.clear()
        while not server._jobs.empty():
            server._jobs.get_nowait()

    def body(self, **kw):
        return {"document_id": DOC, "stage": "transform", "position": 2, "config": {}} | kw

    def test_queues_a_retry_job_and_refuses_while_the_run_is_active(self):
        r = self.client.post("/runs/run-1/retry", json=self.body())
        self.assertEqual(r.status_code, 202)
        job = server._jobs.get_nowait()
        self.assertEqual((job.pipeline_id, job.retry), ("run-1", ("transform", 2)))
        self.assertIs(server._active["run-1"], job)  # so /runs/:id/stop reaches it
        self.assertEqual(self.client.post("/runs/run-1/retry", json=self.body()).status_code, 409)

    def test_rejects_filter_and_split(self):
        for stage in ("filter", "split"):
            r = self.client.post("/runs/run-1/retry", json=self.body(stage=stage))
            self.assertEqual(r.status_code, 422)
        self.assertEqual(self.client.post("/runs/run-1/retry", json=self.body(position=0)).status_code, 422)


if __name__ == "__main__":
    unittest.main()
