"""Run from bem/: uv run python -m unittest discover tests"""

import pathlib
import shutil
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from pipeline import pdftext, pdfutil
from pipeline.steps.validate import apply_verdicts, pixel_box

SIZES = [(1000, 2000)]  # one page, 1000 x 2000 px


def payload():
    return {
        "borehole": {"name": "B 1", "elevation_m": 312.4, "x": 3500000.0, "y": 5400000.0, "epsg": 31467, "metadata": {}},
        "layers": [
            {"position": 1, "depth_from_m": 0.0, "depth_to_m": 2.4, "petrography": "Sand", "color": "grey", "metadata": {}},
            {"position": 2, "depth_from_m": 2.4, "depth_to_m": 5.0, "petrography": "Ton", "color": None, "metadata": {}},
        ],
    }


def check(field, verdict="ok", value=None, message=None, page=1, box=(100, 200, 300, 400)):
    return {"field": field, "page": page, "box": list(box) if box else None, "verdict": verdict,
            "corrected_value": value, "message": message}  # fmt: skip


class Boxes(unittest.TestCase):
    def test_pixel_box_is_normalised_clamped_or_dropped(self):
        self.assertEqual(pixel_box([100, 200, 300, 400], 1, SIZES, {}), [0.1, 0.1, 0.3, 0.2])
        self.assertEqual(pixel_box([-50, 0, 1200, 2400], 1, SIZES, {}), [0.0, 0.0, 1.0, 1.0])
        for raw, page in (([300, 200, 100, 400], 1), ([1, 2, 3], 1), (None, 1), ([1, 2, 3, 4], 2), (["a", 0, 1, 1], 1)):
            self.assertIsNone(pixel_box(raw, page, SIZES, {}), (raw, page))

    def test_tighten_to_words_inside_or_keep(self):
        boxes = [[0.10, 0.10, 0.15, 0.12], [0.16, 0.10, 0.25, 0.12], [0.6, 0.6, 0.7, 0.7]]
        words = [(b, "w") for b in boxes]
        self.assertEqual(pdftext.tighten([0.08, 0.05, 0.3, 0.2], words), [0.10, 0.10, 0.25, 0.12])
        self.assertEqual(pdftext.tighten([0.3, 0.3, 0.4, 0.4], words), [0.3, 0.3, 0.4, 0.4])  # no word inside
        self.assertEqual(pdftext.tighten([0.3, 0.3, 0.4, 0.4], None), [0.3, 0.3, 0.4, 0.4])  # scan
        # a word whose centre is just outside the box is caught by the margin
        self.assertEqual(pdftext.tighten([0.0, 0.0, 0.195, 0.2], words[1:2]), boxes[1])

    def test_snap_to_the_written_value_near_the_model_box(self):
        label, value, other = [0.10, 0.10, 0.30, 0.12], [0.35, 0.10, 0.40, 0.12], [0.35, 0.80, 0.40, 0.82]
        words = [(label, "PETICIONARIO:"), (value, "UTE"), (other, "UTE")]
        # the model box sits on the label; the value next to it wins, the far one is ignored
        self.assertEqual(pdftext.snap([0.15, 0.09, 0.30, 0.13], words, ["UTE"]), value)
        depth = [(value, "9,40")]
        self.assertEqual(pdftext.snap([0.30, 0.09, 0.45, 0.13], depth, [9.4]), value)  # 9,40 is 9.4
        # not found near the box: fall back to the words inside it
        self.assertEqual(pdftext.snap([0.05, 0.09, 0.32, 0.13], words, ["Agadir"]), label)


class TextLayer(unittest.TestCase):
    def pdf(self, tmp: pathlib.Path, rotate: int = 0) -> pathlib.Path:
        w = PdfWriter()
        page = w.add_blank_page(width=200, height=100)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})  # fmt: skip
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        content = StreamObject()
        content.set_data(b"BT /F1 10 Tf 20 80 Td (Depth 2.40) Tj ET")
        page[NameObject("/Contents")] = w._add_object(content)
        if rotate:
            page.rotate(rotate)
        path = tmp / "t.pdf"
        with path.open("wb") as f:
            w.write(f)
        return path

    def test_page_pixel_sizes_follow_dpi_and_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(pdfutil.page_pixel_sizes(self.pdf(pathlib.Path(tmp)), 144), [(400, 200)])
            self.assertEqual(pdfutil.page_pixel_sizes(self.pdf(pathlib.Path(tmp), 90), 144), [(200, 400)])

    @unittest.skipIf(shutil.which("pdftotext") is None, "poppler not installed")
    def test_words_are_normalised_with_origin_top_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            words = pdftext.words(self.pdf(pathlib.Path(tmp)))
        self.assertEqual(list(words), [1])
        self.assertEqual(len(words[1]), 2)  # "Depth", "2.40"
        (x0, y0, x1, y1), text = words[1][0]
        self.assertEqual(text, "Depth")
        self.assertAlmostEqual(x0, 0.1, places=2)  # 20 pt of 200
        self.assertTrue(0.05 < y0 < y1 < 0.3)  # baseline at 80 of 100 pt from the bottom


class ApplyVerdicts(unittest.TestCase):
    def test_corrected_uncertain_wrong_and_sources(self):
        verdicts = {
            "borehole_fields": [
                check("name"),
                check("elevation_m", "corrected", "321.4", "digits swapped"),
                check("location", "uncertain", message="x may be 3500100"),
                check("client", "wrong", message="not the client named", page=None),
                check("bogus", "wrong"),
            ],
            "layers": [
                {"position": 1, "page": 1, "box": [0, 1000, 1000, 1100],
                 "field_boxes": [{"field": "depth_to_m", "page": 1, "box": [0, 1080, 100, 1100]},
                                 {"field": "bogus", "page": 1, "box": [0, 0, 10, 10]},
                                 {"field": "color", "page": None, "box": None}],
                 "fields": [{"field": "petrography", "verdict": "corrected", "corrected_value": "sand, schluffig", "message": "silty"}]},
                {"position": 2, "page": 1, "box": None,
                 "fields": [{"field": "depth_to_m", "verdict": "corrected", "corrected_value": None, "message": "?"}]},
                {"position": 9, "page": 1, "box": None, "fields": []},
            ],
        }  # fmt: skip
        out, flags, edits = apply_verdicts(payload(), verdicts, SIZES, {})
        b = out["borehole"]
        self.assertEqual(b["elevation_m"], 321.4)
        self.assertEqual(out["layers"][0]["petrography"], "Sand, schluffig")
        self.assertEqual(out["layers"][1]["depth_to_m"], 5.0)  # an unusable correction is not applied
        self.assertEqual(
            edits,
            [{"field": "elevation_m", "layer_position": None, "old_value": 312.4, "new_value": 321.4, "reason": "digits swapped"},
             {"field": "petrography", "layer_position": 1, "old_value": "Sand", "new_value": "Sand, schluffig", "reason": "silty"}],
        )  # fmt: skip
        self.assertEqual(
            [(f["field"], f["layer_position"], f["severity"], f["origin"]) for f in flags],
            [("location", None, "warning", "validator"), ("client", None, "error", "validator"),
             ("depth_to_m", 2, "warning", "validator")],
        )  # fmt: skip
        self.assertIn("not applied", flags[2]["message"])
        self.assertEqual(set(b["sources"]), {"name", "elevation_m", "location"})  # client has no page
        self.assertEqual(b["sources"]["name"], {"page": 1, "box": [0.1, 0.1, 0.3, 0.2]})
        self.assertEqual(out["layers"][0]["source"], {"page": 1, "box": [0.0, 0.5, 1.0, 0.55]})
        self.assertEqual(out["layers"][1]["source"], {"page": 1, "box": None})
        self.assertEqual(out["layers"][0]["sources"], {"depth_to_m": {"page": 1, "box": [0.0, 0.54, 0.1, 0.55]}})
        self.assertEqual(out["layers"][1]["sources"], {})
        self.assertEqual(payload()["borehole"]["elevation_m"], 312.4)  # input untouched

    def test_location_correction_and_epsg_guess_flag(self):
        p = payload()
        p["borehole"]["metadata"]["epsg_guessed_by_ai"] = "project names Munich"
        verdicts = {"borehole_fields": [check("location", "corrected", {"x": 3500100, "y": 5400000, "epsg": None})], "layers": []}
        out, flags, edits = apply_verdicts(p, verdicts, SIZES, {})
        self.assertEqual((out["borehole"]["x"], out["borehole"]["epsg"]), (3500100.0, 31467))
        self.assertEqual(edits[0]["old_value"], {"x": 3500000.0, "y": 5400000.0, "epsg": 31467})
        self.assertEqual(flags, [{"field": "location", "layer_position": None, "severity": "warning", "origin": "rule",
                                  "code": "epsg_guessed", "suggestion": None,
                                  "message": "EPSG 31467 is an AI guess: project names Munich"}])  # fmt: skip

    def test_epsg_guess_joins_the_validators_own_location_flag(self):
        p = payload()
        p["borehole"]["metadata"]["epsg_guessed_by_ai"] = "place is Morocco"
        verdicts = {"borehole_fields": [check("location", "uncertain", message="no system written")], "layers": []}
        _, flags, _ = apply_verdicts(p, verdicts, SIZES, {})
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["origin"], "validator")
        self.assertEqual(flags[0]["message"], "no system written (EPSG 31467 is an AI guess: place is Morocco)")

    def test_flags_carry_a_usable_suggestion(self):
        verdicts = {
            "borehole_fields": [
                check("elevation_m", "uncertain", "312.9", "last digit blurred"),
                check("client", "wrong", None, "not the client named"),
                check("total_depth_m", "uncertain", "about five", "?"),
                check("name", "corrected", "", "name unreadable"),
            ],
            "layers": [{"position": 1, "page": 1, "box": None,
                        "fields": [{"field": "petrography", "verdict": "uncertain", "corrected_value": "kies", "message": "or gravel"}]}],
        }  # fmt: skip
        out, flags, edits = apply_verdicts(payload(), verdicts, SIZES, {})
        self.assertEqual(
            [(f["field"], f["severity"], f["suggestion"]) for f in flags],
            [("elevation_m", "warning", 312.9), ("client", "error", None), ("total_depth_m", "warning", None),
             ("name", "warning", None), ("petrography", "warning", "Kies")],
        )  # fmt: skip
        self.assertIn("not applied", flags[3]["message"])  # a correction that cannot be applied
        self.assertEqual((out["borehole"]["elevation_m"], out["layers"][0]["petrography"], edits), (312.4, "Sand", []))


class RenderPages(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pdftoppm"), "needs poppler")
    def test_leftover_pages_of_an_earlier_render_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf, dest = pathlib.Path(tmp) / "one.pdf", pathlib.Path(tmp) / "pages"
            w = PdfWriter()
            w.add_blank_page(72, 72)
            w.write(pdf)
            dest.mkdir()
            for n in (1, 2, 3):
                (dest / f"p-{n}.jpg").write_bytes(b"old")
            self.assertEqual([p.name for p in pdfutil.render_page_images(pdf, dest, 20)], ["p-1.jpg"])
            self.assertNotEqual((dest / "p-1.jpg").read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
