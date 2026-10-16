"""
Send OCR text of a borehole log to Claude and get structured JSON back.

Usage:
    python llm_call.py ocr_text.txt
    python llm_call.py ocr_text.txt --model claude-sonnet-5-5
    cat ocr_text.txt | python llm_call.py -

Needs env var ANTHROPIC_API_KEY.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

DEFAULT_MODEL = "claude-haiku-5-5"


# ----------------------------------------------------------------------------
# 1. Data model (edit this to match your predefined dataset)
# ----------------------------------------------------------------------------
class Layer(BaseModel):
    depth_from_raw: str | None = Field(None, description="Top of layer, exactly as printed, incl. unit")
    depth_to_raw: str | None = Field(None, description="Bottom of layer, exactly as printed, incl. unit")
    depth_from_m: float | None = Field(None, description="Top of layer in metres, only if printed in metres")
    depth_to_m: float | None = Field(None, description="Bottom of layer in metres, only if printed in metres")
    depth_mode: str = Field(
        "interval",
        description="'interval' if the log lists layers with from/to; "
        "'sample_point' if it only lists one depth per sample",
    )
    depth_reference: str | None = Field(
        None, description="'depth_below_surface' or 'elevation' (e.g. 'm ü. NN', 'cota')"
    )
    stratigraphy_raw: str | None = Field(None, description="Stratigraphy / formation text or code, verbatim")
    lithology_raw: str | None = Field(None, description="Rock/soil description, verbatim, original language")
    classification: str | None = Field(None, description="Soil class code if printed (USCS e.g. SM, CH, DIN 4022)")
    color: str | None = Field(None, description="Colour if described in text")
    source_snippet: str = Field(..., description="Short verbatim text snippet this row was taken from")


class Borehole(BaseModel):
    name: str | None = Field(None, description="Borehole name / ID")
    purpose: str | None = Field(None, description="Purpose of borehole (Bohrzweck)")
    drilling_method: str | None = Field(None, description="Drilling method (Bohrart)")
    date: str | None = Field(None, description="Drilling date as printed")
    x_raw: str | None = Field(None, description="X / easting / longitude as printed")
    y_raw: str | None = Field(None, description="Y / northing / latitude as printed")
    crs_raw: str | None = Field(None, description="Coordinate system as printed, e.g. '32U', 'Gauss-Krüger'")
    end_depth_raw: str | None = Field(None, description="Final depth as printed, incl. unit")
    collar_elevation_raw: str | None = Field(None, description="Collar/ground elevation as printed, incl. unit")
    groundwater_raw: str | None = Field(None, description="Groundwater level as printed, incl. unit")
    language: str | None = Field(None, description="Language of the document, ISO code")
    layers: list[Layer] = Field(default_factory=list)
    notes: str | None = Field(None, description="Anything ambiguous or unreadable the reviewer should know")


# ----------------------------------------------------------------------------
# 2. Prompt
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = """You extract data from OCR text of geological/geotechnical borehole logs.
The text may be in any language, may contain OCR errors, and may have lost its table structure.

Rules:
- Copy numbers and units EXACTLY as printed (keep decimal commas in the *_raw fields). Never compute, convert or infer values.
- Fill the numeric *_m fields only when the value is printed in metres and unambiguous; otherwise use null.
- Keep lithology and stratigraphy text verbatim in the original language. Do not translate.
- If a field is not present in the text, use null. Do not guess.
- If the log lists one depth per sample instead of layer intervals, set depth_mode to 'sample_point'.
- If the text contains several boreholes, return only the first one and mention the others in notes.
- For every layer, include a short verbatim source_snippet.
- Report ambiguities or suspected OCR errors in notes.
"""


# ----------------------------------------------------------------------------
# 3. API call
# ----------------------------------------------------------------------------
def extract(text: str, model: str) -> dict:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[
            {
                "name": "save_borehole",
                "description": "Save the extracted borehole data.",
                "input_schema": Borehole.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": "save_borehole"},
        messages=[{"role": "user", "content": f"OCR text of the borehole log:\n\n<ocr>\n{text}\n</ocr>"}],
    )

    print(
        f"[usage] input={response.usage.input_tokens} output={response.usage.output_tokens} "
        f"stop_reason={response.stop_reason}",
        file=sys.stderr,
    )
    if response.stop_reason == "max_tokens":
        print("[warn] output was cut off -> increase max_tokens or split the text", file=sys.stderr)

    for block in response.content:
        if block.type == "tool_use":
            # validate against the model (raises if the shape is wrong)
            return Borehole.model_validate(block.input).model_dump()
    raise RuntimeError("Model did not return a tool call")


# ----------------------------------------------------------------------------
# 4. Simple checks in plain code (the LLM does not do these)
# ----------------------------------------------------------------------------
def to_float(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    return float(m.group().replace(",", ".")) if m else None


def validate(data: dict, source_text: str) -> list[str]:
    issues = []
    layers = data.get("layers", [])

    prev_to = None
    for i, layer in enumerate(layers, start=1):
        f = layer["depth_from_m"] if layer["depth_from_m"] is not None else to_float(layer["depth_from_raw"])
        t = layer["depth_to_m"] if layer["depth_to_m"] is not None else to_float(layer["depth_to_raw"])
        if f is not None and t is not None and layer["depth_reference"] != "elevation" and f >= t:
            issues.append(f"layer {i}: from ({f}) >= to ({t})")
        if prev_to is not None and f is not None and abs(f - prev_to) > 0.01:
            issues.append(f"layer {i}: gap/overlap, previous ended at {prev_to}, this starts at {f}")
        prev_to = t if t is not None else prev_to

        # every printed number should exist in the source text
        for key in ("depth_from_raw", "depth_to_raw"):
            val = to_float(layer[key])
            if val is not None:
                pattern = re.escape(str(layer[key]).split()[0])
                if not re.search(pattern, source_text):
                    issues.append(f"layer {i}: {key}='{layer[key]}' not found in OCR text (hallucination?)")

    end_depth = to_float(data.get("end_depth_raw"))
    if layers and end_depth is not None and prev_to is not None and abs(prev_to - end_depth) > 0.01:
        issues.append(f"last layer ends at {prev_to}, but end depth is {end_depth}")

    if not layers:
        issues.append("no layers extracted")
    return issues


# ----------------------------------------------------------------------------
# 5. CLI
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="text file with OCR text, or - for stdin")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", help="output json path (default: <input>.json)")
    args = ap.parse_args()

    text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")

    data = extract(text, args.model)
    issues = validate(data, text)
    result = {"data": data, "validation_issues": issues, "needs_review": bool(issues)}

    out_path = Path(args.out) if args.out else Path("stdout.json" if args.input == "-" else args.input + ".json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[saved] {out_path}", file=sys.stderr)
    if issues:
        print(f"[review] {len(issues)} issue(s) found, see validation_issues", file=sys.stderr)


if __name__ == "__main__":
    main()
