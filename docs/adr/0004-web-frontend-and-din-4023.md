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
