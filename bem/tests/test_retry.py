"""Run from bem/: uv run python -m unittest discover tests"""

import contextlib
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
TRANSFORMED = {"payload": {"borehole": {"name": "B"}, "layers": []}, "validation_issues": ["i"]}


def fake_step(stage, seen, result=None):
    """A step that records its input and succeeds for its one borehole."""

    def step(items, out_dir, report, workers, recorder, first_position):
        seen[stage] = (items[0], first_position)
        recorder.start(stage, report, position=first_position)
        recorder.record(stage, result or {}, report=report, position=first_position)
        return [result or {}]

    return step


def patched(seen, **overrides):
    steps = {
        "transform_boreholes": fake_step("transform", seen, TRANSFORMED),
        "validate_boreholes": fake_step("validate", seen, {"payload": {}}),
    } | overrides
    return [mock.patch.object(server, name, f) for name, f in steps.items()] + [
        mock.patch.object(server.RunTracker, "_store_borehole", return_value="b1")
    ]


class ProcessRetry(unittest.TestCase):
    def job(self, stage, position=1):
        return server.Job(DOC, "run-1", PipelineConfig(), retry=(stage, position))

    def run_retry(self, api, stage, **overrides):
        seen = {}
        with contextlib.ExitStack() as stack:
            for p in patched(seen, **overrides):
                stack.enter_context(p)
            return server.process_retry(self.job(stage), api), seen

    def test_transform_retry_uses_stored_extraction_then_validates_and_completes_the_run(self):
        api = FakeApi([row("transform", 1, "failed"), row("extract", 1, "success", {"warnings": ["w"]}), SPLIT])
        (status, error), seen = self.run_retry(api, "transform")

        self.assertEqual((status, error), ("completed", None))
        self.assertEqual(seen["transform"][0][1], {"warnings": ["w"]})
        pdf, extracted, transformed = seen["validate"][0]
        self.assertEqual((pdf.name, extracted, transformed, seen["validate"][1]), ("BH1.pdf", {"warnings": ["w"]}, TRANSFORMED, 1))
        self.assertEqual(api.downloads, [SPLIT_DOC])  # validate reads the page images
        # the new attempts are new rows linked to the source and split documents
        self.assertEqual(api.created[0], ("transform", 1, "running", [DOC, SPLIT_DOC]))
        self.assertEqual(api.created[1][:3], ("validate", 1, "running"))

    def test_validate_retry_uses_newest_successful_transform_and_extract_warnings(self):
        older = {"payload": {"old": True}}
        api = FakeApi([
            row("validate", 1, "failed"), row("transform", 1, "success", TRANSFORMED), row("transform", 1, "failed"),
            row("transform", 1, "success", older), row("extract", 1, "success", {"warnings": ["w"]}), SPLIT,
        ])  # fmt: skip
        (status, error), seen = self.run_retry(api, "validate")

        self.assertEqual((status, error), ("completed", None))
        self.assertNotIn("transform", seen)
        self.assertEqual(seen["validate"][0][1:], ({"warnings": ["w"]}, TRANSFORMED))
        self.assertEqual([c[0] for c in api.created], ["validate"])

    def test_validate_retry_without_transform_result_fails(self):
        api = FakeApi([row("validate", 1, "failed"), row("transform", 1, "failed"), SPLIT])
        (status, error), seen = self.run_retry(api, "validate")
        self.assertEqual(status, "failed")
        self.assertIn("transform result is missing", error)
        self.assertEqual(seen, {})

    def test_extract_retry_downloads_split_pdf_and_failure_keeps_run_failed(self):
        api = FakeApi([row("extract", 1, "failed"), SPLIT])

        def fake_extract(files, out_dir, report, workers, recorder, first_position):
            self.assertEqual(files[0].name, "BH1.pdf")
            recorder.start("extract", report, position=first_position)
            raise server.PipelineError("model said no")

        (status, error), seen = self.run_retry(api, "extract", extract_boreholes=fake_extract)

        self.assertEqual(api.downloads, [SPLIT_DOC])
        self.assertEqual(seen, {})  # transform and validate never ran
        self.assertEqual(status, "failed")
        self.assertIn("extract #1", error)

    def test_extract_retry_continues_with_transform_and_validate(self):
        api = FakeApi([row("validate", 1, "new"), row("transform", 1, "new"), row("extract", 1, "failed"), SPLIT])
        def fake_extract(files, out_dir, report, workers, recorder, first_position):
            recorder.start("extract", report, position=first_position)
            recorder.record("extract", {"warnings": []}, report=report, position=first_position)
            return [(files[0], {"warnings": []})]

        (status, error), seen = self.run_retry(api, "extract", extract_boreholes=fake_extract)
        self.assertEqual((status, error), ("completed", None))
        self.assertEqual(seen["validate"][0][1:], ({"warnings": []}, TRANSFORMED))

    def test_other_failed_jobs_keep_the_run_failed(self):
        api = FakeApi(
            [row("validate", 2, "failed"), row("transform", 1, "failed"), row("extract", 2, "failed"),
             row("extract", 1, "success", {}), SPLIT]
        )  # fmt: skip
        (status, error), _ = self.run_retry(api, "transform")

        self.assertEqual(status, "failed")
        self.assertEqual(error, "2 job(s) not successful: extract #2, validate #2")

    def test_missing_split_result_fails_without_running_anything(self):
        status, error = server.process_retry(self.job("extract"), FakeApi([row("filter", None, "success")]))
        self.assertEqual(status, "failed")
        self.assertIn("split result is missing", error)

    def test_validate_retry_reuses_a_borehole_an_earlier_attempt_stored(self):
        # the earlier attempt stored the borehole but its row was left running, then stopped
        api = FakeApi([
            row("validate", 1, "stopped"), row("validate", 1, "failed", {"borehole_id": "bh-old"}),
            row("transform", 1, "success", TRANSFORMED), row("extract", 1, "success", {}), SPLIT,
        ])  # fmt: skip
        api.upload_borehole = mock.Mock()
        seen = {}
        with mock.patch.object(server, "validate_boreholes", fake_step("validate", seen, {"payload": {}})):
            status, error = server.process_retry(self.job("validate"), api)

        self.assertEqual((status, error), ("completed", None))
        api.upload_borehole.assert_not_called()
        self.assertEqual(api.stages[0]["data"]["borehole_id"], "bh-old")


class SuccessReport(unittest.TestCase):
    def tracker(self, failures):
        api = FakeApi([])
        update = api.update_exec_stage

        def flaky(stage_id, status, **fields):
            if status == "success" and failures:
                failures.pop()
                raise server.ApiError("503")
            return update(stage_id, status, **fields)

        api.update_exec_stage = flaky
        api.upload_borehole = mock.Mock(return_value={"data": {"id": "bh1"}})
        t = server.RunTracker(api, "run-1", DOC)
        t.started("validate", 1, "sonnet", "high")
        return t, api

    def test_success_update_is_retried_after_storing_the_borehole(self):
        t, api = self.tracker([1, 1])
        with mock.patch.object(server, "SUCCESS_BACKOFF_S", 0):
            t.succeeded("validate", 1, {"payload": {"borehole": {}, "layers": []}}, [], None)
        self.assertEqual((api.stages[0]["status"], api.stages[0]["data"]["borehole_id"]), ("success", "bh1"))
        api.upload_borehole.assert_called_once()

    def test_gives_up_after_the_last_attempt(self):
        t, api = self.tracker([1] * server.SUCCESS_ATTEMPTS)
        with mock.patch.object(server, "SUCCESS_BACKOFF_S", 0), self.assertRaises(server.ApiError):
            t.succeeded("validate", 1, {"payload": {"borehole": {}, "layers": []}}, [], None)
        self.assertEqual(api.stages[0]["status"], "running")


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

    def test_accepts_validate(self):
        self.assertEqual(self.client.post("/runs/run-2/retry", json=self.body(stage="validate")).status_code, 202)

    def test_rejects_filter_and_split(self):
        for stage in ("filter", "split"):
            r = self.client.post("/runs/run-1/retry", json=self.body(stage=stage))
            self.assertEqual(r.status_code, 422)
        self.assertEqual(self.client.post("/runs/run-1/retry", json=self.body(position=0)).status_code, 422)


if __name__ == "__main__":
    unittest.main()
