---
id: ADR-0006
date: 2026-11-18
author: Manuel Di Biase
title: Validation stage and human review
---

# ADR-0006 – Validation stage and human review

## Context

The challenge metric asks for *reliable* extraction. Until now the pipeline stored whatever the extractor returned; uncertainty only survived as free-text `warnings` and `validation_issues` strings in the transform job's JSON. Worse, `din4023.conform` blocked the upload of a whole borehole for one unknown soil term or overlapping layer, so the data was lost instead of reviewed. Nothing linked an extracted value back to where it stands in the document, and boreholes could not be edited (`POST` only, the `/edit` page was a stub).

## Decision

### Pipeline: a fifth stage `validate`

`filter → split → extract → transform → validate`, one `validate` job per borehole like extract and transform, with its own `{model, effort}` in the run config (default `sonnet`/`high`; independence comes from the fresh context, not from a different model: in a test on a sample log Sonnet and Opus found the same problems, but Sonnet's boxes were much tighter (Opus drew overlapping boxes around whole intervals) at about half the cost). It is always on.

- **Input:** the pages of the borehole's split-out PDF as images, the transform payload, the extractor's `warnings` and the pipeline's own issues (DIN normalisation, EPSG guess). It gets a fresh context, not the extractor's reasoning.
- **Output** (`schemas.VALIDATE`): for every borehole field and every layer, the page and a pixel box where it is written, and a verdict: `ok`, `corrected` (the validator is sure the value is wrong and knows the right one; it is applied), `uncertain` (doubtful; an optional suggested value is stored on the flag as `suggestion`, nothing is applied) or `wrong` (contradicts the document, correct value unknown).
- **Boxes:** one per borehole field, one per layer row and one per layer field (depths, description, stratigraphy, colour). Pixel boxes on the page image are normalised to `[x0, y0, x1, y1]` in 0–1 of the page, origin top left. If the PDF has a text layer (`pdftotext -bbox`, poppler, no new dependency), a box snaps to the written value near it (numbers compared as numbers, so `9,40` matches 9.4), else it is tightened to the words inside it. Scans keep the model's box.
- **Storing:** `validate` posts the borehole (`POST /api/boreholes`), so it is stored once, complete with flags; transform no longer posts. A failed validate job is retried like extract/transform (`POST /exec_stages/:id/retry`); retrying extract or transform also reruns validate.
- `din4023.conform` no longer blocks: an unknown soil term becomes `petrography: null` with the original in `metadata.petrography_original`; ordering and overlap problems are left to the API checks. The API's changeset rules (name present, depths ≥ 0, `depth_to_m > depth_from_m`) still reject a borehole.

### Data model (API)

| Where | What |
|---|---|
| `boreholes.sources` (jsonb) | `{"<field>": {"document_id", "page", "box"}}` per borehole field (`location` stands for the coordinates) |
| `borehole_layers.source` / `sources` (jsonb) | the whole row/interval, and `{"<field>": {...}}` per layer field |
| `boreholes.source_x` / `source_y` / `source_epsg` | the coordinates as written in the document, set with `location`; the review shows these (comparable with the log) and the WGS84 position below |
| `boreholes.verified_at` | set with `verified` |
| `field_flags` | `borehole_id`, `layer_id` (nullable, no foreign key: flags of a deleted layer are hidden and come back when it is restored), `field`, `severity` (`warning`/`error`), `message`, `suggestion` (any JSON, the validator's proposed value), `origin` (`rule`/`validator`), `code` (rule id, null for validator flags), `resolved_at`, `resolved_by` (`human`/`rule`) |
| `field_edits` | append-only history: `borehole_id`, `layer_id` (nullable, **no** foreign key so history survives a deleted layer), `field`, `old_value`, `new_value` (any JSON), `source` (`validator`/`human`), `reason`, `inserted_at` |

`field` names are the API column names (`elevation_m`, `depth_to_m`, …), `location` for coordinates (values `{"x", "y", "epsg"}`) and `layer` for creating/deleting a whole layer (the value is the layer's snapshot; `old_value: null` is a creation, `new_value: null` a deletion). `documents.raw_extraction` stays unused.

### Plausibility checks (API, one place)

`Api.Boreholes.Checks` runs after create and after every edit and keeps the `rule` flags of its own codes in sync: opens new ones, resolves (`resolved_by: rule`) those that no longer apply. Codes: `no_layers`, `layer_gap`, `layer_overlap`, `total_depth_mismatch` (total depth ≠ last layer bottom, 5 cm tolerance), `groundwater_below_bottom`, `missing_elevation`, `missing_location`, `missing_petrography` (mentions `metadata.petrography_original` if present). Open rule flags get their message updated when the values change. Rule flags with other codes (`epsg_guessed` from the pipeline, `unknown_epsg` when a borehole arrives with an EPSG code PostGIS does not know; it is then stored without location) are not touched by the checks. A rule flag a human confirmed ("looks right") is not reopened until that field is edited again. Layer `position` is always the rank by `depth_from_m`, renumbered after every layer change.

### Edit and review API

- `PATCH /api/boreholes/:id` `{"borehole": {...}}`, `POST /api/boreholes/:id/layers` `{"layer": {...}}`, `PATCH|DELETE /api/boreholes/:id/layers/:layer_id`: one `field_edits` row (`source: human`) per changed field, open flags on an edited field are resolved (`resolved_by: human`), then the checks run. Coordinates are edited as `x`/`y`/`epsg` like on create; an unknown EPSG code is a `422`, and x/y that land off the globe in their EPSG too. Typed without an EPSG code, degrees are taken as 4326; for metres `GET /api/boreholes/:id/epsg_guess` finds the system from nearby boreholes or the borehole's own rough position, and if there is neither the review asks for a click on the rough area of a map, whose UTM zone then decides. Accepting a validator suggestion is a normal edit of that field.
- `POST /api/boreholes/:id/edits/:edit_id/revert`: writes the edit's `old_value` back as a new human edit (undo; restoring a deleted layer re-inserts it with its old id). History is never rewritten.
- `POST /api/flags/:id/resolve`: a human confirms a value ("looks right").
- `POST /api/boreholes/:id/verify` `{"verified": true|false}`: release; allowed with open flags (the UI asks first).
- `GET /api/boreholes/:id` adds `sources`, `verified_at`, `open_flag_count`, `flags` (open first) and `edits` (newest first); layers add `source`. List and `view=points` features add `open_flag_count`; `sort=open_flags` and `flagged=true|false` filter; the search language gets `verified:` and `flagged:` (`yes`/`no`).
- `POST /api/boreholes` also accepts `borehole.sources`, `layers[].source`, `flags` and `edits` (validator corrections); both refer to layers by `layer_position`.

### Web

**Review page layout and flow.** No tabs: one scrolling column (header data in groups, then the layer table beside a sticky DIN profile) with a sticky jump bar, a draggable splitter to the PDF (default 40/60), and the borehole's split-out PDF shown by default. Hovering a value zooms and pans the PDF smoothly to its box (CSS transform on a high-resolution render, spotlight outside the box) and zooms back out on leave; a focused field keeps the zoom. Saves use the API response (no reload), Enter/Tab save and move on. Flag messages show under the field with "Looks right" and, for suggestions, "Apply". A progress bar counts done flags; after the last one the page offers to release, then "Next borehole". A sidebar entry **Review** (count of unverified boreholes) opens the next unverified borehole, most open flags first. Keys: `N` next flag, `Ctrl+Enter` looks right.

**Duplicate uploads.** `documents.sha256` is stored on upload; before starting an extraction the web hashes each file and asks `GET /api/documents?sha256=`. A known file shows when it was processed with "Open existing" or "Process again anyway".

The review page becomes the editing page (the `/edit` stub goes): fields on the left edit inline (saved on Enter/blur), layers can be added and deleted, petrography is picked from the DIN 4023 list. Marks: yellow/red for open warning/error flags, blue for "corrected by validator", a separate mark for "edited by a human"; each field has ↶ (revert the last edit) and a history popover. The PDF viewer gets an overlay: hovering a field, a layer row or a layer in the DIN profile shows its box (switching page if needed). A "next flag" button walks the open flags; the borehole list sorts by open flags; the map draws verified boreholes filled and unverified ones hollow, with an open-flag badge in lists and detail.

## Pros

- Uncertain values are visible per field and fixable in place, next to the exact spot in the source.
- Nothing is lost to a blocked upload; every change (validator or human) is traceable and reversible.
- Checks live once, in the API, so they apply to pipeline results and human edits alike.
- No new dependency: boxes come from the model, tightened with poppler where a text layer exists.

## Cons

- One more model call per borehole (cost, time), about as expensive as extract.
- Model boxes on scans are approximate.
- Adding a stage touches the hardcoded stage lists in `bem`, the API and the web.
- Without auth, "human" is not a person; the history cannot say who edited.

## Alternatives

- **OCR (Tesseract) for boxes:** pixel-exact on clean scans, but a new system dependency, weak on old scans, and OCR alone cannot tell which "2.40" belongs to which field; the model is needed for the mapping anyway.
- **Gemini for boxes:** trained for bounding boxes, but we keep to Claude models.
- **Validator only flags, never corrects:** less risk, but more manual work; corrections are logged and revertible, so the risk is small.
- **Checks in bem:** they would not rerun after a human edit.

## Consequences

- `exec_stages.type` gains `validate`; the run completes only if the newest extract, transform and validate row of every borehole succeeded.
- `mix boreholes.mock` generates flags and validator edits (no boxes: mock documents share one example file).
- Auth, if ever added, can fill a user column on `field_edits` without changing the model.

## References

- ADR-0001 (data model, API as source of truth), ADR-0002 (pipeline runs and stage tracking), ADR-0003 (search language), ADR-0004 (web layering, DIN 4023)
- `bem/pipeline/steps/validate.py`, `api/lib/api/boreholes/checks.ex`, `web/src/routes/borehole/[id]/review/`
