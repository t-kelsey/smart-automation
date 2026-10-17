"""Step 1: OCR text -> Bohrung, using a Qwen model behind an OpenAI-compatible server.

Example server (vLLM):
    vllm serve Qwen/Qwen3-32B --port 8000
Any server that supports `response_format={"type": "json_schema"}` works
(vLLM, SGLang, llama.cpp server, Ollama's OpenAI endpoint, ...).
"""
from __future__ import annotations

from openai import OpenAI
from pydantic import ValidationError

from .schema import Bohrung

SYSTEM_PROMPT = """You extract borehole data from OCR text of German borehole reports \
(Bohrprofile / Schichtenverzeichnisse) into JSON.

Rules:
- Use ONLY information that is explicitly in the text. Never guess, infer or complete.
- Unknown values: null for numbers, date, boolean and coordinate parts;
  "Unbekannt" for bohrzweck and bohrart; "keine Angabe" for a layer's stratigraphie / petrographie.
- Keep names, stratigraphy and petrography in the original German wording. Do not translate or normalise.
- Numbers: convert decimal comma to decimal point (112,0 -> 112.0). Depths are metres below ground.
- bohrdatum: ISO format YYYY-MM-DD.
- koordinaten: zone like "32U"; ost = Rechtswert (easting), nord = Hochwert (northing), exactly as written.
- ansatzhoehe_m: collar elevation in m ü. NN.
- schichten: one entry per layer, in depth order. von_m = top, bis_m = bottom of that layer.
- lgrb_geprueft: true/false only if the text states it, otherwise null.
Return only the JSON object."""


def make_client(base_url: str = "http://localhost:8000/v1", api_key: str = "EMPTY") -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def extract(text: str, client: OpenAI, model: str, max_retries: int = 2) -> Bohrung:
    """Run the extraction. Retries only if the output fails Pydantic parsing
    (rare with constrained decoding, e.g. an unparseable date)."""
    schema = Bohrung.model_json_schema()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"OCR text:\n\n{text}"},
    ]
    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "bohrung", "strict": True, "schema": schema},
            },
            # Qwen3 hybrid models: switch off thinking mode. Other models ignore this.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = resp.choices[0].message.content or ""
        try:
            return Bohrung.model_validate_json(content)
        except ValidationError as e:
            last_error = e
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"The JSON was invalid: {e}\nReturn a corrected JSON object."},
            ]
    raise RuntimeError(f"Extraction failed after retries: {last_error}")
