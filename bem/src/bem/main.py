"""Run the borehole pipeline: OCR -> translation and labeling -> triage -> extraction -> output.

Usage:
    python -m bem.main <file-or-dir>... [--to api|json|print] [--api-url BASE_URL] [--out-dir DIR]
"""

import argparse
import logging
import os
from pathlib import Path

from bem.ocr import ocr_file
from bem.translation_and_labeling.translation_and_labeling import translate
from bem.triage import split
from bem.extraction import extract
from bem.api import ApiClient, document_id_from_stem
from bem.output import make_sink
from bem.schema import Borehole as PipelineBorehole

log = logging.getLogger("bem")

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx"}
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def collect_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories into the supported files they contain."""
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
        else:
            files.append(path)
    return files


def save_stage(stage: str, path: Path, content: str, suffix: str = ".md") -> None:
    """Write one stage's output to output/<stage>/<parent folder>__<input stem><suffix> (debug only).

    The folder prefix keeps apart inputs that share a file name (e.g. Report01.pdf).
    """
    out_dir = OUTPUT_DIR / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{path.parent.name}__{path.stem}{suffix}").write_text(content, encoding="utf-8")


def process_file(path: Path, sink, debug: bool, client: ApiClient | None = None) -> int:
    """Push every borehole found in one input file through the pipeline. Returns the count.

    With debug, the output of OCR, translation, triage and extraction is saved under output/.
    With a client, each stage result is also reported to the API, if the file is a tracked
    document (its name is a document ID, ADR-0014). Boreholes are created either way.
    """
    document_id = document_id_from_stem(path.stem)
    if client and not document_id:
        log.warning("%s: file name is not a document ID, boreholes are created without stage tracking", path.name)
    track = client if document_id else None

    # STAGE 1 - OCR: any format -> markdown (every page is OCR'd)
    document = ocr_file(path)              
    if debug:
        save_stage("ocr", path, document)
    if track:
        track.put_stage(document_id, "ocr", {"markdown": document})

    # STAGE 2 - translation: local terms -> English, keywords labeled
    document, translate_errors = translate(document)
    if debug:
        save_stage("translate", path, document)
    if track:
        track.put_stage(document_id, "translation", {"translated_markdown": document, "translate_errors": translate_errors})

    sections = split(path.name, document)  # one Borehole per borehole ID
    if track:
        track.put_triage_sections(document_id, sections)

    count = 0
    failures = []
    for i, section in enumerate(sections):
        if debug:
            save_stage("triage", path, section.raw_markdown, f"__{i}.md")

        record = extract(section.raw_markdown).model_copy(update={
            "name": section.name,
            "external_id": section.external_id,
            "source_file": section.source_file,
            "translate_errors": section.translate_errors,
        })
        
        if debug:
            save_stage("extract", path, record.model_dump_json(indent=2), f"__{i}.json")
        if track:
            track.put_extraction_result(document_id, i, record)

        try:
            created_id = sink(record, document_id)
        except Exception as e:
            # Report the failure, then go on with the other sections of this file.
            log.exception("%s: borehole %s not delivered", path.name, record.name)
            failures.append(record.name)
            if track:
                response = getattr(e, "response", None)
                status = response.status_code if response is not None else None
                track.put_sink_result(document_id, i, {"success": False, "response_status": status, "error": str(e)})
            continue
        if track:
            track.put_sink_result(document_id, i, {"success": True, "response_status": 201, "created_borehole_id": created_id})
        count += 1
    if failures:
        raise RuntimeError(f"{len(failures)} borehole(s) not delivered: {', '.join(failures)}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--to", choices=["api", "json", "print"], default="print")
    parser.add_argument("--api-url", default=os.environ.get("BEM_API_URL", "http://localhost:4000/api"))
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    parser.add_argument("--debug", action="store_true", help="save intermediate stages to output/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    client = ApiClient(args.api_url)
    failed = []
    with make_sink(args.to, client=client, out_dir=args.out_dir) as sink:
        for path in collect_inputs(args.inputs):
            try:
                count = process_file(path, sink, args.debug, client if args.to == "api" else None)
                log.info("%s: %d borehole(s)", path.name, count)
            except Exception:
                log.exception("failed: %s", path)
                failed.append(path)

    if failed:
        raise SystemExit(f"{len(failed)} file(s) failed: {', '.join(str(p) for p in failed)}")


if __name__ == "__main__":
    main()
