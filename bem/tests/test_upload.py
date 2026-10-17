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
        self.api.create_exec_stage("extract", "r1", {"a": 1}, ["d1"], position=2)
        self.api.upload_report("d1", "r1", [{"step": "x"}])
        self.assertEqual(self.calls[0], ("POST", "/api/exec_stages", {"type": "extract", "run_id": "r1", "position": 2, "data": {"a": 1}, "document_ids": ["d1"]}))
        self.assertEqual(self.calls[1], ("POST", "/api/reports", {"document_id": "d1", "run_id": "r1", "data": {"steps": [{"step": "x"}]}}))

    def test_borehole_is_normalised_or_blocked(self):
        self.api.upload_borehole({"borehole": {"name": "B"}, "layers": [layer("sand")]}, "d1")
        method, path, body = self.calls[0]
        self.assertEqual((method, path, body["document_id"], body["layers"][0]["petrography"]), ("POST", "/api/boreholes", "d1", "Sand"))
        with self.assertRaises(din4023.Din4023Error):
            self.api.upload_borehole({"borehole": {"name": "B"}, "layers": [layer("clay")]}, "d1")
        self.assertEqual(len(self.calls), 1)  # the violating borehole was never sent

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


if __name__ == "__main__":
    unittest.main()
