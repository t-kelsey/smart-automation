"""The four pipeline steps. Each writes its intermediate output below `out_dir`."""

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from . import pdfutil, schemas
from .naming import base, stamped
from .claude_cli import PipelineError, StepReport, log, run_claude

MAX_READ_PAGES = 20  # the Read tool renders at most 20 PDF pages per call


def _dump(path: pathlib.Path, data) -> None:
    path = stamped(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------
# Step 1: keep only real borehole log pages            (haiku, high effort)
# --------------------------------------------------------------------------

FILTER_PROMPT = """Read every page of the PDF at {path} ({n} pages, use the Read tool's
`pages` parameter, e.g. "1-{n}"). Classify each page.

Keep a page (is_borehole_log=true) only if it is a real borehole log sheet: a drilling
log / core log / Bohrprofil / Schichtenverzeichnis / sondage / columna estratigrafica,
i.e. a graphic or tabular profile with depth and layer descriptions for one borehole.
Continuation sheets of a log also count.

Reject everything else: cover pages, tables of contents, running report text, maps and
site plans, cross sections, legends/standards pages, lab or test result tables, photos,
blank pages. When unsure whether a page is part of a log, keep it.

Return one entry per page, numbered 1..{n} within this file. Give your final answer
only through the structured output, not as prose."""


def filter_pages(
    pdf: pathlib.Path, out_dir: pathlib.Path, report: StepReport, chunk_size: int, workers: int
) -> tuple[pathlib.Path, list[str]] | None:
    """Returns (PDF with only borehole log pages, one hint per kept page), or None if there are none."""
    step_dir = out_dir / "01_filter"
    total = pdfutil.page_count(pdf)
    log(f"step 1: {total} pages, classifying in chunks of {chunk_size}")

    chunks = []
    for i, start in enumerate(range(1, total + 1, chunk_size), 1):
        end = min(start + chunk_size - 1, total)
        chunk_pdf = stamped(step_dir / "chunks" / f"chunk_{i:03d}_p{start}-{end}.pdf")
        pdfutil.write_pages(pdf, range(start, end + 1), chunk_pdf)
        chunks.append((chunk_pdf, start, end))

    def classify(chunk):
        chunk_pdf, start, end = chunk
        n = end - start + 1
        result = run_claude(
            FILTER_PROMPT.format(path=chunk_pdf, n=n),
            model="haiku",
            effort="high",
            schema=schemas.CLASSIFY_PAGES,
            report=report,
            add_dirs=[out_dir],
        )
        by_page = {p["page"]: p for p in result["pages"]}
        rows = []
        for rel in range(1, n + 1):
            p = by_page.get(rel)
            rows.append(
                {
                    "page": start + rel - 1,
                    # never silently drop a page the model skipped
                    "is_borehole_log": p["is_borehole_log"] if p else True,
                    "reason": p["reason"] if p else "not classified by model, kept",
                }
            )
        return rows

    with ThreadPoolExecutor(workers) as pool:
        pages = [row for rows in pool.map(classify, chunks) for row in rows]

    kept = [p["page"] for p in pages if p["is_borehole_log"]]
    _dump(step_dir / "classification.json", {"source": str(pdf), "total_pages": total, "kept_pages": kept, "pages": pages})
    log(f"step 1: keeping {len(kept)} of {total} pages")
    if not kept:
        return None
    dest = stamped(step_dir / "borehole_pages.pdf")
    pdfutil.write_pages(pdf, kept, dest)
    hints = [p["reason"] for p in pages if p["is_borehole_log"]]
    return dest, hints


# --------------------------------------------------------------------------
# Step 2: one file per borehole                         (haiku, medium effort)
# --------------------------------------------------------------------------

SPLIT_PROMPT = """Read the PDF at {path} ({n} pages). It contains borehole log sheets
only. Work out which pages belong to which borehole and group them: every borehole gets
one entry with its page numbers (1..{n}, ascending). Continuation sheets belong to the
borehole they continue. Every page must be assigned to exactly one borehole.

{read_hint}
Use the borehole name/id written on the sheet as the label.

A previous pass noted this about each page (it may be wrong, check the pages):
{page_hints}

Give your final answer only through the structured output, not as prose."""


def split_boreholes(
    pages_pdf: pathlib.Path, out_dir: pathlib.Path, report: StepReport, page_hints: list[str]
) -> list[pathlib.Path]:
    step_dir = out_dir / "02_split"
    n = pdfutil.page_count(pages_pdf)
    hint = (
        f"The Read tool shows at most {MAX_READ_PAGES} pages per call, so read in ranges "
        f'such as "1-{MAX_READ_PAGES}", "{MAX_READ_PAGES + 1}-{2 * MAX_READ_PAGES}", ...'
        if n > MAX_READ_PAGES
        else f'Read all pages with pages "1-{n}".'
    )
    prompt = SPLIT_PROMPT.format(
        path=pages_pdf,
        n=n,
        read_hint=hint,
        page_hints="\n".join(f"- page {i}: {h}" for i, h in enumerate(page_hints, 1)),
    )
    log(f"step 2: grouping {n} pages into boreholes")

    for attempt in (1, 2):
        result = run_claude(
            prompt,
            model="haiku",
            effort="medium",
            schema=schemas.SPLIT_BOREHOLES,
            report=report,
            add_dirs=[out_dir],
            max_turns=6 + n // MAX_READ_PAGES * 2,
        )
        _dump(step_dir / f"raw_response_attempt{attempt}.json", result)  # for debugging bad groupings

        # validate: pages in range, none used twice, none forgotten
        seen: set[int] = set()
        groups = []
        for g in result["boreholes"]:
            pages = sorted({p for p in g["pages"] if 1 <= p <= n} - seen)
            seen |= set(pages)
            if pages:
                groups.append({"label": g["label"], "pages": pages})
        missing = sorted(set(range(1, n + 1)) - seen)
        if groups and not missing:
            break
        log(f"step 2: attempt {attempt}/2 unusable: {len(groups)} group(s), unassigned pages {missing}")
    else:
        raise PipelineError(
            f"step 2 could not group the pages into boreholes; see raw_response_attempt*.json in {step_dir}"
        )

    files = []
    for i, g in enumerate(groups, 1):
        dest = stamped(step_dir / f"borehole_{i:02d}.pdf")
        pdfutil.write_pages(pages_pdf, g["pages"], dest)
        g["file"] = dest.name
        files.append(dest)
    _dump(step_dir / "grouping.json", {"boreholes": groups})
    log(f"step 2: {len(files)} borehole file(s): " + "; ".join(f"{g['label']} = pages {g['pages']}" for g in groups))
    return files


# --------------------------------------------------------------------------
# Step 3: extract everything from one borehole          (sonnet, high effort)
# --------------------------------------------------------------------------

EXTRACT_PROMPT = """Read the borehole log PDF at {path} ({n} pages; the Read tool shows at
most {max_pages} pages per call). It should contain exactly ONE borehole.

First check that: set is_single_borehole and borehole_count_in_file accordingly. If it
holds several boreholes, extract only the first one and say so in warnings.

Then extract all data: header data, coordinates (exactly as written, plus parsed
numbers if unambiguous), elevation, depths, groundwater, and EVERY layer with its depth
interval. Layers carry meaning in colour and hatch pattern too: use them for
petrography/colour where the text doesn't say. Keep all text in the document's original
language and wording; do not translate here. Use null for anything not in the document,
never guess. Put anything that fits no field into other_information, and list
illegible or doubtful parts in warnings."""


def extract_boreholes(
    files: list[pathlib.Path], out_dir: pathlib.Path, report: StepReport, workers: int
) -> list[tuple[pathlib.Path, dict]]:
    step_dir = out_dir / "03_extract"
    log(f"step 3: extracting {len(files)} borehole(s)")

    def extract(f: pathlib.Path):
        n = pdfutil.page_count(f)
        data = run_claude(
            EXTRACT_PROMPT.format(path=f, n=n, max_pages=MAX_READ_PAGES),
            model="sonnet",
            effort="high",
            schema=schemas.EXTRACT_BOREHOLE,
            report=report,
            add_dirs=[out_dir],
            max_turns=8 + n // MAX_READ_PAGES * 2,
        )
        _dump(step_dir / f"{base(f.stem)}.json", data)
        if not data["is_single_borehole"]:
            log(f"step 3: WARNING {f.name} holds {data['borehole_count_in_file']} boreholes")
        return f, data

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(extract, files))


# --------------------------------------------------------------------------
# Step 4: format/translate to the database schema       (haiku, high effort)
# --------------------------------------------------------------------------

TRANSFORM_PROMPT = """Convert this borehole extraction into the payload for our database
API (POST /api/boreholes). Input JSON:

{data}

Rules:
- Translate all free text to English, but keep proper nouns (place, client, person and
  project names) unchanged.
- borehole.name: the borehole designation (e.g. "B 1/59"), never null; fall back to
  the project or place name only if no designation exists.
- Dates: ISO YYYY-MM-DD, null if not fully determinable. Do not invent day or month.
- Coordinates: set x, y and epsg only if all three are known (x = easting/longitude,
  y = northing/latitude, epsg = integer code for the stated coordinate system, e.g.
  31467 for Gauss-Krueger zone 3). Otherwise set all three to null. Always keep the
  original text in source_coordinate_raw and the system name in source_coordinate_system.
- Depths and elevation in metres, plain numbers. Depths are measured from the surface,
  >= 0, and each layer's depth_to_m must be greater than depth_from_m.
- layers: keep order, position starts at 1.
  - stratigraphy: formation/age as a short English term or the formation abbreviation
    plus its name if known; null if absent.
  - petrography: the main soil or rock type as a standard English DIN 4023 term
    (e.g. "clay", "silty sand", "limestone"), lowercase.
  - color: English colour words only (e.g. "grey-brown"), null if absent.
  - raw_text: the original layer description exactly as extracted (untranslated).
  - metadata: remaining layer details as string key/value pairs (e.g. notes), else {{}}.
- borehole.metadata: string key/value pairs for useful header data the columns have no
  place for (project, source_language, date notes, other_information entries, warnings).
  Leave out is_single_borehole and borehole_count_in_file; they are bookkeeping.
- Do not add facts that are not in the input."""


def transform_boreholes(
    extracted: list[tuple[pathlib.Path, dict]], out_dir: pathlib.Path, report: StepReport, workers: int
) -> list[dict]:
    step_dir = out_dir / "04_transform"
    log(f"step 4: transforming {len(extracted)} borehole(s) to the database schema")

    def transform(item: tuple[pathlib.Path, dict]):
        f, data = item
        payload = run_claude(
            TRANSFORM_PROMPT.format(data=json.dumps(data, ensure_ascii=False, indent=1)),
            model="haiku",
            effort="high",
            schema=schemas.DB_PAYLOAD,
            report=report,
            tools="",
            max_turns=2,
        )
        issues = validate_payload(payload)
        for i in issues:
            log(f"step 4: WARNING {f.stem}: {i}")
        _dump(step_dir / f"{base(f.stem)}.json", {"payload": payload, "validation_issues": issues})
        return {"payload": payload, "validation_issues": issues, "source_file": f.name}

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(transform, extracted))


def validate_payload(p: dict) -> list[str]:
    """Mirror the API's changeset rules locally so problems show before posting."""
    issues = []
    b = p["borehole"]
    if not (b.get("name") or "").strip():
        issues.append("borehole.name is empty (API requires it)")
    for k in ("total_depth_m", "borehole_length_m", "elevation_m", "groundwater_level_m"):
        if b.get(k) is not None and b[k] < 0:
            issues.append(f"borehole.{k} is negative (API requires >= 0)")
    xyz = [b.get("x"), b.get("y"), b.get("epsg")]
    if any(v is None for v in xyz) and not all(v is None for v in xyz):
        issues.append("x, y, epsg must be all set or all null")
    for l in p["layers"]:
        pos = l["position"]
        if l["depth_from_m"] < 0 or l["depth_to_m"] <= l["depth_from_m"]:
            issues.append(f"layer {pos}: invalid depth range {l['depth_from_m']}..{l['depth_to_m']}")
    return issues
