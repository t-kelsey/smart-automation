"""Run from bem/: uv run python -m unittest discover tests"""

import json
import unittest

import httpx

from pipeline import din4023
from pipeline.api_service import ApiError, ApiService, api_base_url


def layer(petro, a=0.0, b=1.0, **kw):
    return {"position": 1, "depth_from_m": a, "depth_to_m": b, "stratigraphy": None, "petrography": petro,
            "color": "grey", "raw_text": "x", "metadata": {}, **kw}


class Din4023(unittest.TestCase):
    def test_normalises_to_standard_spelling(self):
        n = din4023.normalise_petrography
        self.assertEqual(n("sand"), "Sand")
        self.assertEqual(n("sand,schluffig"), "Sand, schluffig")
        self.assertEqual(n("S, u, g"), "Sand, schluffig, kiesig")
        self.assertEqual(n("Torf/Humus"), "Torf, Humus")
        self.assertEqual(n("Torf, Humus, sandig"), "Torf, Humus, sandig")
        self.assertEqual(n("Loess"), "Löss")
        self.assertEqual(n("Steine"), "Stein")
        self.assertEqual(n("sandstein"), "Sandstein")

    def test_rejects_unknown(self):
        n = din4023.normalise_petrography
        for bad in (None, "", "clay", "Sand, glittery", "schluffig", "Sand, Kies"):
            self.assertIsNone(n(bad), bad)

    def test_conform_keeps_original_and_flags_issues(self):
        out, issues = din4023.conform({"borehole": {}, "layers": [layer("sand, schluffig"), layer("clay", 1, 2)]})
        self.assertEqual(out["layers"][0]["petrography"], "Sand, schluffig")
        self.assertEqual(out["layers"][0]["metadata"]["petrography_original"], "sand, schluffig")
        self.assertEqual(len(issues), 1)
        self.assertIn("clay", issues[0])

    def test_depth_rules(self):
        _, issues = din4023.conform({"layers": [layer("Sand", 0, 2), layer("Ton", 1, 3)]})
        self.assertEqual(len(issues), 1)
        _, issues = din4023.conform({"layers": []})
        self.assertEqual(issues, ["no layers"])


class Service(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def handler(req: httpx.Request) -> httpx.Response:
            self.calls.append((req.method, req.url.path, json.loads(req.content)))
            return httpx.Response(201, json={"data": {}})

        self.api = ApiService("localhost:4000", httpx.Client(transport=httpx.MockTransport(handler)))

    def test_base_url(self):
        self.assertEqual(api_base_url("localhost:4000"), "http://localhost:4000/api")
        self.assertEqual(api_base_url("http://api:4000/api/"), "http://api:4000/api")

    def test_exec_stage_and_report(self):
        self.api.create_exec_stage("extract", "r1", ["d1"], 2, status="running", model="sonnet", error=None)
        self.api.update_exec_stage("s1", "success", data={"a": 1}, usage={"calls": 1})
        self.api.upload_report("d1", "r1", [{"step": "x"}])
        self.api.set_pipeline_run_status("p1", "failed", "boom")
        self.assertEqual(self.calls[0], ("POST", "/api/exec_stages", {"type": "extract", "run_id": "r1", "position": 2, "status": "running", "document_ids": ["d1"], "model": "sonnet"}))
        self.assertEqual(self.calls[1], ("PUT", "/api/exec_stages/s1", {"status": "success", "data": {"a": 1}, "usage": {"calls": 1}}))
        self.assertEqual(self.calls[2], ("POST", "/api/reports", {"document_id": "d1", "run_id": "r1", "data": {"steps": [{"step": "x"}]}}))
        self.assertEqual(self.calls[3], ("PUT", "/api/pipeline_runs/p1/status", {"status": "failed", "error": "boom"}))

    def test_borehole_is_normalised_or_blocked(self):
        self.api.upload_borehole({"borehole": {"name": "B"}, "layers": [layer("sand")]}, "d1", ["s1"])
        method, path, body = self.calls[0]
        self.assertEqual(body["additional_document_ids"], ["s1"])
        self.assertEqual((method, path, body["document_id"], body["layers"][0]["petrography"]), ("POST", "/api/boreholes", "d1", "Sand"))
        with self.assertRaises(din4023.Din4023Error):
            self.api.upload_borehole({"borehole": {"name": "B"}, "layers": [layer("clay")]}, "d1")
        self.assertEqual(len(self.calls), 1)  # the violating borehole was never sent

    def test_upload_document_returns_id(self):
        import pathlib, tempfile

        seen = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen["path"], seen["ctype"], seen["body"] = req.url.path, req.headers["content-type"], req.content
            return httpx.Response(202, json={"data": {"id": "new-id"}})

        api = ApiService("localhost:4000", httpx.Client(transport=httpx.MockTransport(handler)))
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "b.pdf"
            f.write_bytes(b"%PDF-1.7 x")
            self.assertEqual(api.upload_document(f, "BH_1.pdf"), "new-id")
        self.assertEqual(seen["path"], "/api/documents")
        self.assertTrue(seen["ctype"].startswith("multipart/form-data"))
        self.assertIn(b'name="file"; filename="BH_1.pdf"', seen["body"])

    def test_download_checks_for_pdf(self):
        import pathlib, tempfile

        def serve(content, status=200):
            return ApiService("localhost:4000", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, content=content))))

        with tempfile.TemporaryDirectory() as tmp:
            dest = pathlib.Path(tmp) / "d.pdf"
            serve(b"%PDF-1.7 ...").download_document("d1", dest)
            self.assertEqual(dest.read_bytes(), b"%PDF-1.7 ...")
            with self.assertRaises(ApiError):
                serve(b"PK docx").download_document("d1", dest)
            self.assertFalse(dest.exists())
            with self.assertRaises(ApiError):
                serve(b"", 404).download_document("d1", dest)


class EventTracker:
    def __init__(self):
        self.events = []

    def started(self, stage, position, model, effort):
        self.events.append(("started", stage, position, model))

    def succeeded(self, stage, position, data, files, usage):
        self.events.append(("succeeded", stage, position, usage["calls"] if usage else None))

    def failed(self, stage, position, error, usage):
        self.events.append(("failed", stage, position, type(error).__name__))


class RecorderTest(unittest.TestCase):
    def test_failure_is_reported_once(self):
        from pipeline.ai import PipelineError
        from pipeline.output import Recorder

        tracker = EventTracker()
        recorder = Recorder(tracker)
        error = PipelineError("claude exited with 1")
        recorder.record_failure("extract", error, position=2)
        recorder.record_failure("extract", error)  # re-raised further up: must not be reported twice
        self.assertEqual(tracker.events, [("failed", "extract", 2, "PipelineError")])

    def test_start_reports_model_and_raises_when_stopped(self):
        import threading

        from pipeline.ai import PipelineStopped, StepReport, Usage
        from pipeline.output import Recorder

        tracker = EventTracker()
        recorder = Recorder(tracker)
        stop = threading.Event()
        step = StepReport("3 extract", "sonnet", "high", stop=stop)
        part = step.child("#1")
        recorder.start("extract", part, position=1)
        part.add(Usage(calls=1, cost_usd=0.5))
        recorder.record("extract", {}, report=part, position=1)
        self.assertEqual(step.usage.calls, 1)  # the borehole's usage counts towards the step
        stop.set()
        with self.assertRaises(PipelineStopped):
            recorder.start("extract", step.child("#2"), position=2)
        self.assertEqual(tracker.events, [("started", "extract", 1, "sonnet"), ("succeeded", "extract", 1, 1)])

    def test_tracking_errors_do_not_abort(self):
        from pipeline.output import Recorder

        class Broken(EventTracker):
            def succeeded(self, *a):
                raise RuntimeError("API down")

        Recorder(Broken()).record("filter", {})


class RunTrackerTest(unittest.TestCase):
    """The server's tracker against a fake API: planning, split uploads, borehole storage, stop."""

    def setUp(self):
        import pathlib
        import tempfile

        from pipeline.server import RunTracker

        self.calls = []
        counter = iter(range(1, 1000))
        documents = iter(range(1, 1000))

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/documents":
                self.calls.append(("POST", "/api/documents", None))
                return httpx.Response(202, json={"data": {"id": f"split{next(documents)}"}})
            body = json.loads(req.content)
            self.calls.append((req.method, req.url.path, body))
            if req.url.path == "/api/boreholes":
                if body["borehole"]["name"] == "bad":
                    return httpx.Response(422, json={"errors": {}})
                return httpx.Response(201, json={"data": {"id": "bh1"}})
            return httpx.Response(200, json={"data": {"id": f"stage{next(counter)}"}})

        self.api = ApiService("localhost:4000", httpx.Client(transport=httpx.MockTransport(handler)))
        self.tracker = RunTracker(self.api, "run1", "doc1")
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = pathlib.Path(self.tmp.name) / "b.pdf"
        self.pdf.write_bytes(b"%PDF-1.7 x")

    def tearDown(self):
        self.tmp.cleanup()

    def stage_calls(self):
        return [(m, p, b.get("type"), b.get("position"), b["status"]) for m, p, b in self.calls if "exec_stages" in p]

    def test_lifecycle(self):
        from pipeline.ai import PipelineStopped

        t = self.tracker
        t.plan()
        t.started("split", None, "haiku", "medium")
        t.succeeded("split", None, {"boreholes": [{"label": "B 1", "pages": [1]}, {"label": "B 2", "pages": [2]}]}, [self.pdf, self.pdf], {"calls": 1})
        t.started("transform", 1, "haiku", "high")
        t.succeeded("transform", 1, {"payload": {"borehole": {"name": "B"}, "layers": [layer("sand")]}, "validation_issues": []}, [], None)
        t.succeeded("transform", 2, {"payload": {"borehole": {"name": "bad"}, "layers": [layer("sand")]}, "validation_issues": []}, [], None)
        t.failed("extract", 2, PipelineStopped("run stopped"), None)

        stages = self.stage_calls()
        self.assertEqual(stages[:2], [("POST", "/api/exec_stages", "filter", None, "new"), ("POST", "/api/exec_stages", "split", None, "new")])
        self.assertEqual(stages[2][0::4], ("PUT", "running"))
        self.assertEqual(stages[3][0::4], ("PUT", "success"))
        split_update = [b for m, p, b in self.calls if m == "PUT" and b["status"] == "success"][0]
        self.assertEqual(split_update["document_ids"], ["split1", "split2"])
        # after split: extract/transform planned per borehole, linked to their split PDF
        planned = [(b["type"], b["position"], b["document_ids"]) for m, p, b in self.calls if m == "POST" and "exec_stages" in p][2:6]
        self.assertEqual(planned, [("extract", 1, ["doc1", "split1"]), ("transform", 1, ["doc1", "split1"]),
                                   ("extract", 2, ["doc1", "split2"]), ("transform", 2, ["doc1", "split2"])])
        borehole = [b for m, p, b in self.calls if p == "/api/boreholes"][0]
        self.assertEqual((borehole["document_id"], borehole["additional_document_ids"]), ("doc1", ["split1"]))
        updates = [b for m, p, b in self.calls if m == "PUT"]
        self.assertEqual(updates[3]["status"], "success")
        self.assertEqual(updates[3]["data"]["borehole_id"], "bh1")
        self.assertEqual(updates[4]["status"], "failed")  # the API refused borehole 2
        self.assertTrue(updates[4]["error"].startswith("upload: ApiError"))
        self.assertEqual(updates[5]["status"], "stopped")
        self.assertEqual(len(t.upload_errors), 1)


class ImageToPdf(unittest.TestCase):
    def test_converts_png_and_multiframe_tiff(self):
        import pathlib, tempfile
        from PIL import Image
        from pipeline import pdfutil

        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            a, b = Image.new("RGB", (50, 80), "white"), Image.new("L", (50, 80), 128)
            a.save(tmp / "a.png")
            a.save(tmp / "m.tif", save_all=True, append_images=[b])
            pdfutil.image_to_pdf(tmp / "a.png", tmp / "a.pdf")
            pdfutil.image_to_pdf(tmp / "m.tif", tmp / "m.pdf")
            self.assertEqual(pdfutil.page_count(tmp / "a.pdf"), 1)
            self.assertEqual(pdfutil.page_count(tmp / "m.pdf"), 2)
            (tmp / "x.png").write_bytes(b"nope")
            with self.assertRaises(ValueError):
                pdfutil.image_to_pdf(tmp / "x.png", tmp / "x.pdf")


if __name__ == "__main__":
    unittest.main()
