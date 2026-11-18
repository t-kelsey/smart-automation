---
id: ADR-0004
date: 2026-11-18
author: Tyler Kelsey
title: Web frontend stack, layered API-only data access and the shared DIN 4023 standard
---

# ADR-0004 – Web frontend stack, layered API-only data access and the shared DIN 4023 standard

## Context

The challenge needs an interactive world map of georeferenced boreholes, a detail view that draws the log like a geologist expects, and upload and monitoring pages. The frontend must be developed independently of the backend but show only what the backend holds. Lithology must follow one standard across the pipeline, the API and the web app, because the pipeline, the database and the drawing all need the same vocabulary.

## Decision

**Stack.** SvelteKit 3 with Svelte 5 (runes) and TypeScript in `web/`. MapLibre GL JS renders the map from GeoJSON served by the API in WGS84; no coordinate conversion in the frontend. MapLibre was chosen over Mapbox GL JS, which needs an API key and billing.

**Layering.** Dependencies point one way: UI → service → repository interface → API repository.

- UI (`src/routes`, `src/lib/components`) imports only services and domain types. An ESLint `no-restricted-imports` rule enforces this.
- Services (`src/lib/services`) hold use-case logic and take a repository in their constructor.
- Repositories (`src/lib/repositories/api`) return domain types (`src/lib/domain`). DTOs and mappers stay inside the API repository folder.
- One composition root, `createServices({ fetch })` in `src/lib/services/index.ts`, wires the API repositories and passes SvelteKit's `fetch`.

**API only.** All data comes from the API; `pnpm dev` needs the API on `localhost:4000`, reached through the Vite proxy at `/api`. The faker-based mock repositories remain in `src/lib/repositories/mock/`, unwired; `PUBLIC_MOCK_BOREHOLES` stays because `mock-data.ts` reads it. A mock can be wired back in at the composition root.

**Mapping.** The API repository translates API fields into domain types (e.g. `purpose` → `cause`, `drilled_at` → `date`, `depth_from_m`/`depth_to_m` → `startDepth`/`endDepth`). Free-text layer fields (petrography, colour, stratigraphy) are parsed best effort. Fields the API lacks are optional in the domain and hidden in the UI.

**DIN 4023 drawing.** The engine is pure TypeScript in `web/src/lib/din4023/` with no UI dependencies: materials from Tables 1–3, Annex A colours, hatch definitions, the composition model, short-form and description formatting, and a free-text parser (English only, heuristic).

- A layer's petrography is a structured `Composition`: main component, secondary components with weak or strong proportion, and an optional breakdown for anthropogenic fill. Until the API stores compositions, `parseComposition` derives them from free text and returns nothing when unrecognised.
- The column shows a white background, an optional colour tint, the main hatch across the full width, the first secondary hatch on the right half, depth labels at boundaries and a short form (e.g. `G/S, u'`) per layer.
- Hatches are SVG `<pattern>` definitions created once and referenced by id.
- Groundwater, samples and property symbols are not drawn yet.
- Where the 2023 tables differ from the 2006 hatch sheet, the 2023 tables win.

**Shared standard file.** `standards/din-4023/din-4023.json` is the single language-neutral source for `bem`, `api` and `web`, in German as in the standard. It contains:

- `schraffuren`: the 47 hatches of the 2006-02 sheet, each with a stable ASCII `id`, label, category, short form and source table.
- `tabelle_1`: the 17 pure soil types of Table 1 (2023-02), with short forms, hatch id and colour. Rows added in 2023 are marked with `hinweis`.
- `farben`: Annex A colours (RGB, hex, RAL).
- `norm`: edition and source metadata.

The file holds names, short forms and colour values only, no hatch artwork; drawing stays in `web`. Known source conflicts are kept as printed and annotated, e.g. "türkis" (RGB 98, 213, 196 vs. hex #28A9B2); rendering uses the hex value, as in `colors.ts`.

**Map detail view.** The map has a 3D detail view, switched on with a button from zoom 11 on (the map leaves it when zoomed out further):

- The map tilts (pitch 60°); circles and clusters are replaced by one column per borehole, drawn with MapLibre `fill-extrusion` (no extra 3D library). The perspective camera stands in for a true isometric projection.
- Columns rise above the ground: the surface layer is on top and the deepest layer stands on the map. Height is the depth exaggerated 10×. The footprint is a fixed 40 m wide at every zoom (the earlier zoom-dependent size at zoom 16). The column data is only rebuilt when newly loaded boreholes arrive; zooming and panning never redraw it, which keeps the view fluent. The outline has 48 sides, and MapLibre's `fill-extrusion-rounded-corner-distance` is set so the walls are shaded as one curved surface; the hatch then wraps around the column with one seam on the north side, away from the camera. MapLibre 6.14 textures each wall backwards (the wall's end vertex gets the smaller edge distance), so on a many-sided column every face showed its slice of the hatch mirrored. `web/patches/maplibre-gl@6.14.0.patch` (pnpm `patchedDependencies`) fixes this in the worker bundle the app loads; it is about 1 MB because the bundle is minified into very long lines. A MapLibre upgrade needs the patch redone (or dropped once fixed upstream), and the web Docker build copies `web/patches/` before installing.
- Each layer segment shows the DIN hatch of its main material (`columnFill(composition).main`) on its DIN colour, tinted 50 % as in the profile column, as a `fill-extrusion-pattern`. The tiles are drawn with Canvas 2D (`column-patterns.ts`) so they can be added synchronously before each redraw. Unclassified layers are plain grey; depth gaps between layers stay empty.
- Layers come from one bulk request per area (`GET /api/boreholes?view=columns&bbox=…`, ADR-0001), loaded with a margin around the view and cached, so small pans send no request.
- Hovering a segment wraps it in a translucent blue sleeve and shows the borehole card right of the pointer (not above, so the other layers stay reachable), with that layer's depth range and material. The card follows the pointer from layer to layer and stays open while the pointer is on it; map events under the card are ignored.
- The column model (`web/src/lib/borehole-columns/column-model.ts`) is independent of MapLibre. A planned side-on view (a section along a line drawn on the map, boreholes at true distance) reuses it and the same data.

**Section view.** A *Section* button (top-down and detail view) draws a straight line with two clicks; Esc cancels. The map previews the line and a rounded 100 m corridor around it (also beyond its ends) and rings the caught boreholes (blue sleeves in the detail view). *Show section* opens a full-screen side view and puts `section=lon1,lat1,lon2,lat2` in the URL (SvelteKit shallow routing: Back closes it, a reload or link opens it directly); the map stays mounted underneath.

- Boreholes are placed at their distance along the line (projection onto the line, in a local equirectangular frame) and aligned at their start: depth 0 is one line for all, elevation is not used.
- Horizontal and vertical scales fill the screen independently; the resulting vertical exaggeration is shown. Columns are 60 px wide and pushed apart where they would overlap; a dashed leader marks the true position on the distance axis.
- Columns use the profile column's layer drawing (`LayerFill.svelte`, shared with `BoreholeColumn`), without labels; depths are on a shared axis, details in a hover card. Clicking a column opens the borehole page.
- Layers come from the existing `view=columns` request for the line's area; corridor, ordering and prediction are computed in the frontend (`borehole-columns/section.ts`, `correlation.ts`).

**Layer prediction.** Between each pair of neighbouring boreholes the layer sequences are aligned (Needleman–Wunsch): only layers with the same, known main material are connected, layers keep their order (connections never cross), and among equally many connections the ones at more similar depths win. Layers starting below the other borehole's end are not connected, nor are layers whose top or bottom would slope more than 45° at the map's 10× vertical exaggeration (depth change over a tenth of the distance between the boreholes); the angle is measured independently of the screen so the result does not change with the window size. Unconnected layers, including unknown (grey) ones, pinch out halfway: every gap between two connections has one pinch point there, the unconnected layers fan into it and the connected bands bend through it, so the bands fill the space without overlaps. Predicted bands use the hatch and colour of their layer, lighter and with dashed outlines, and can be hidden with a toggle (on by default). Test data: `mix boreholes.section_mock` (`Api.SectionMockData`, ten boreholes along a 1 km line in Stuttgart-Feuerbach).

**Pipeline use.** A borehole whose petrography cannot be mapped to DIN 4023 is not posted, and its run is marked failed (ADR-0002).

## Pros

- Components do not change when the data source changes; mapping knowledge lives in one folder.
- The UI can be built and demoed against the real backend without fake data.
- Geologists read a recognised standard without a custom legend.
- The composition model expresses mixed soils exactly.
- The engine is framework-free and reusable, e.g. for exports.
- One standard file keeps the pipeline, database and drawing in step.
- The lint rule makes the layering checkable.

## Cons

- More files and indirection than a small app strictly needs; the service layer is thin.
- Mappers must follow API changes by hand; nothing checks DTOs against the Ecto schemas.
- The parser is heuristic, lossy and English-only until the API stores compositions.
- The standard's "türkis" colour is inconsistent; one value was chosen.
- Water level, samples and property symbols are not drawn, so some information is lost.
- Tables 2 to 6 of the standard are not covered; rock names appear only as hatch entries.
- The JSON was transcribed by hand from the PDFs and has no automated check.
- The file is derived from a licensed standard. Whether it may be published is not yet confirmed; if not, it moves out of version control and is loaded from `data/`.
- `web/` has no unit test runner; the engine was checked with a Node smoke script and screenshots.

## Alternatives

- **`fetch` directly in load functions:** least code, but the data switch and mapping end up in every route.
- **Context-based DI (`setContext`):** load functions run outside the component tree, so a factory is simpler.
- **A DI container library:** unnecessary for two implementations of one interface.
- **Repositories returning raw DTOs, services mapping:** puts wire knowledge in the service layer.
- **Keep the mock as the default data source:** rejected; the app silently showed data the backend does not hold. Env switching was removed.
- **Keep a custom lithology key:** not standard-conformant and cannot express mixtures.
- **Pre-rendered image hatches:** hard to recolour and do not scale.
- **Render the full standard including property symbols:** judged too complex for the current need.
- **Columns below the ground (three.js custom layer):** closer to reality, but needs a second 3D renderer and a see-through basemap; columns above the ground work with MapLibre alone.
- **True orthographic isometric view:** MapLibre only has a perspective camera; a separate scene would lose the map.
- **Per-borehole detail requests for the columns:** no API change, but hundreds of requests per view.
- **Section as a panel below the map or as a separate page:** the full-screen view gives the section the most room; its URL still makes it shareable.
- **Nearest-borehole or distance-weighted prediction:** simpler or smoother, but they ignore the order of layers; correlation follows how geologists connect logs.
- **Correlation by material group or stratigraphy:** would connect more layers (e.g. sand with gravel), but also wrong ones; the strict rule only connects what is clearly the same.
- **Prediction in the API:** reusable by other clients, but a new endpoint for something the frontend computes instantly from data it already has.
- **Keep the TypeScript module as the only source:** `bem` and `api` cannot read it.
- **Per-component copies (Python dict, Elixir module):** drift is likely.
- **Standard in the database via seeds:** `bem` runs independently of the API.
- **English translations in the standard file:** can be added later as extra fields.
- **Mapbox GL JS:** proprietary, requires an API key and billing.
- **Leaflet:** weaker performance on larger vector datasets.
- **Another framework (React etc.):** would discard the scaffolded app for no clear benefit.

## Consequences

- Adding a new data field means changing the domain type, the API repository and, if needed, the mock.
- Extending the standard (Tables 2 to 6, English labels) means editing `din-4023.json` and recording the change.
- Components that read the standard should reference hatch ids and Table 1 names from the file; migrating the remaining TypeScript tables is a separate step.
- The API should eventually store compositions in structured form; the parser can then be removed.

## References

- `web/src/lib/din4023/`, `web/src/lib/services/index.ts`, `web/src/lib/repositories/api/`
- `web/eslint.config.js` (layering rule)
- `standards/din-4023/din-4023.json`
- DIN 4023:2023-02 and the 2006-02 hatch sheet (`data/Standards_Formats/`, confidential, not committed)
- ADR-0001, ADR-0002
