"""Run from bem/: uv run python -m unittest discover tests"""

import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import httpx
from pydantic import ValidationError

from pipeline import local_vlm
from pipeline.ai import AI, PipelineError, StepReport, new_ai, set_ai
from pipeline.claude_cli import ClaudeCLI
from pipeline.config import PipelineConfig, default_chunk_size, resolve_models
from pipeline.steps import extract, filter as filter_step, split

SCHEMA = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}


def chat(content: str) -> dict:
    return {"message": {"content": content}, "prompt_eval_count": 7, "eval_count": 3, "total_duration": 2_000_000_000}


def vlm(handler) -> local_vlm.LocalVLM:
    return local_vlm.LocalVLM(transport=httpx.MockTransport(handler))


ENV = {"BEM_LOCAL_URL": "http://ollama.test"}


class Config(unittest.TestCase):
    def test_provider_defaults_to_claude(self):
        c = PipelineConfig()
        self.assertEqual(c.provider, "claude")
        self.assertEqual(resolve_models(c)["filter"].model, "haiku")

    def test_rejects_unknown_provider(self):
        with self.assertRaises(ValidationError):
            PipelineConfig.model_validate({"provider": "gpt"})

    def test_local_swaps_claude_names_only(self):
        c = PipelineConfig.model_validate({"provider": "local", "extract": {"model": "my-model", "effort": "low"}})
        with mock.patch.dict(os.environ, {"BEM_LOCAL_MODEL": ""}):
            m = resolve_models(c)
        self.assertEqual(m["filter"].model, "qwen3-vl:2b")  # default "haiku" replaced
        self.assertEqual(m["extract"].model, "my-model")  # explicit local name kept
        with mock.patch.dict(os.environ, {"BEM_LOCAL_MODEL": "qwen3.5:2b"}):
            self.assertEqual(resolve_models(c)["filter"].model, "qwen3.5:2b")

    def test_chunk_size_per_provider(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BEM_CHUNK_SIZE", None)
            os.environ.pop("BEM_LOCAL_CHUNK_SIZE", None)
            self.assertEqual(default_chunk_size("claude"), 10)
            self.assertEqual(default_chunk_size("local"), 2)


class Backends(unittest.TestCase):
    def test_selection(self):
        self.assertIsInstance(new_ai("claude_cli"), ClaudeCLI)
        self.assertIsInstance(new_ai("local"), local_vlm.LocalVLM)
        with self.assertRaises(PipelineError):
            new_ai("nope")

    def test_flags(self):
        self.assertTrue(ClaudeCLI.reads_files)
        self.assertIsNone(ClaudeCLI.max_input_pages)
        self.assertFalse(local_vlm.LocalVLM.reads_files)

    def test_claude_command_unchanged(self):
        out = {"structured_output": {"a": 1}, "usage": {}}
        with mock.patch("subprocess.run") as run:
            run.return_value = mock.Mock(stdout=json.dumps(out))
            r = ClaudeCLI().run(
                "p", model="haiku", effort="high", schema=SCHEMA, report=StepReport("s", "haiku", "high"),
                inputs=[(pathlib.Path("x.pdf"), "1-2")],
            )
        self.assertEqual(r, {"a": 1})
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["claude", "-p", "p"])
        self.assertNotIn("x.pdf", " ".join(cmd))  # inputs are ignored by the CLI backend
        self.assertEqual(cmd[cmd.index("--model") + 1], "haiku")
        self.assertEqual(cmd[cmd.index("--tools") + 1], "Read")


class LocalVLM(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_schema_images_and_fills_usage(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.update(json.loads(request.content), url=str(request.url))
            return httpx.Response(200, json=chat('{"a": 1}'))

        report = StepReport("s", "qwen3-vl:2b", "high", "local")
        with mock.patch.object(local_vlm, "render_pages", return_value=["AAAA", "BBBB"]):
            r = vlm(handler).run(
                "look", model="qwen3-vl:2b", effort="high", schema=SCHEMA, report=report,
                inputs=[(pathlib.Path("x.pdf"), "1-2")],
            )
        self.assertEqual(r, {"a": 1})
        self.assertEqual(seen["url"], "http://ollama.test/api/chat")
        self.assertEqual(seen["format"], SCHEMA)
        self.assertEqual(seen["messages"][0]["images"], ["AAAA", "BBBB"])
        self.assertEqual(seen["model"], "qwen3-vl:2b")
        self.assertEqual((report.usage.input_tokens, report.usage.output_tokens, report.usage.cost_usd), (7, 3, 0.0))
        self.assertEqual(report.usage.models, {"qwen3-vl:2b"})

    def test_retries_bad_json(self):
        answers = iter(["not json", '```json\n{"a": 2}\n```'])
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(200, json=chat(next(answers)))

        report = StepReport("s", "m", "high", "local")
        r = vlm(handler).run("p", model="m", effort="high", schema=SCHEMA, report=report, tools="")
        self.assertEqual(r, {"a": 2})
        self.assertEqual((len(calls), report.usage.calls), (2, 2))

    def test_gives_up_after_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            ai = vlm(lambda r: httpx.Response(200, json=chat("nope")))
            ai.debug_dir = pathlib.Path(tmp)
            with self.assertRaises(PipelineError):
                ai.run("p", model="m", effort="high", schema=SCHEMA, report=StepReport("s", "m", "h", "local"))
            self.assertEqual(len(list(pathlib.Path(tmp).glob("*failed_response_*"))), 2)

    def test_retries_transport_errors(self):
        n = []

        def handler(request):
            n.append(1)
            if len(n) < 3:
                raise httpx.ConnectError("down")
            return httpx.Response(200, json=chat('{"a": 3}'))

        with mock.patch("time.sleep"):
            r = vlm(handler).run("p", model="m", effort="h", schema=SCHEMA, report=StepReport("s", "m", "h", "local"))
        self.assertEqual((r, len(n)), ({"a": 3}, 3))

    def test_http_error_not_retried(self):
        n = []

        def handler(request):
            n.append(1)
            return httpx.Response(404, text="model not found")

        with self.assertRaisesRegex(PipelineError, "404"):
            vlm(handler).run("p", model="m", effort="h", schema=SCHEMA, report=StepReport("s", "m", "h", "local"))
        self.assertEqual(len(n), 1)

    def test_page_cap(self):
        with mock.patch.dict(os.environ, {"BEM_LOCAL_MAX_PAGES": "2"}):
            with self.assertRaisesRegex(PipelineError, "BEM_LOCAL_MAX_PAGES"):
                vlm(lambda r: httpx.Response(200, json=chat("{}"))).run(
                    "p", model="m", effort="h", schema=SCHEMA, report=StepReport("s", "m", "h", "local"),
                    inputs=[(pathlib.Path("x.pdf"), "1-3")],
                )

    def test_not_configured(self):
        with mock.patch.dict(os.environ, {"BEM_LOCAL_URL": ""}):
            self.assertFalse(local_vlm.is_configured())
            with self.assertRaisesRegex(PipelineError, "BEM_LOCAL_URL"):
                local_vlm.LocalVLM().run("p", model="m", effort="h", schema=SCHEMA, report=StepReport("s", "m", "h"))

    def test_parse_range(self):
        self.assertEqual(local_vlm.parse_range("3"), (3, 3))
        self.assertEqual(local_vlm.parse_range("1-4"), (1, 4))
        with self.assertRaises(PipelineError):
            local_vlm.parse_range("4-1")


class FakeAI(AI):
    """Records calls and answers from a canned list; stands in for any backend."""

    def __init__(self, answers, reads_files=False, max_input_pages=None):
        self.answers, self.calls = list(answers), []
        self.reads_files, self.max_input_pages = reads_files, max_input_pages

    def run(self, prompt, *, model, effort, schema, report, tools="Read", add_dirs=None, max_turns=8, inputs=None):
        self.calls.append({"prompt": prompt, "inputs": inputs})
        return self.answers.pop(0)


class Steps(unittest.TestCase):
    def test_prompts_have_no_read_tool_for_local(self):
        for p in (filter_step.FILTER_PROMPT_LOCAL, split.SPLIT_PROMPT_LOCAL, extract.EXTRACT_PROMPT_LOCAL):
            self.assertNotIn("Read tool", p)
            self.assertIn("attached images", p)
        self.assertIn("Read tool", filter_step.FILTER_PROMPT)  # Claude prompts untouched

    def test_split_rejects_too_many_pages_for_local(self):
        with mock.patch("pipeline.pdfutil.page_count", return_value=9):
            with self.assertRaisesRegex(PipelineError, "pages exceed"):
                split.split_boreholes(
                    pathlib.Path("x.pdf"), pathlib.Path("/nonexistent"), StepReport("s", "m", "h"), ["a"] * 9,
                    ai=FakeAI([], max_input_pages=4),
                )

    def test_extract_truncates_and_warns(self):
        data = {"is_single_borehole": True, "borehole_count_in_file": 1, "warnings": []}
        ai = FakeAI([data], max_input_pages=3)
        with mock.patch("pipeline.pdfutil.page_count", return_value=5), tempfile.TemporaryDirectory() as tmp:
            [(_, out)] = extract.extract_boreholes(
                [pathlib.Path("b.pdf")], pathlib.Path(tmp), StepReport("s", "m", "h"), 1, ai=ai
            )
        self.assertEqual(ai.calls[0]["inputs"], [(pathlib.Path("b.pdf"), "1-3")])
        self.assertIn("first 3 of 5", out["warnings"][0])


if __name__ == "__main__":
    unittest.main()
