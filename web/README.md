# web

Web frontend of the geodatabase: explore, search and review boreholes and start the extraction pipeline.

## Why it exists

The extracted data is only useful if people can find and judge it. The web app shows boreholes on an interactive world map (top-down, or as a tilted 3D detail view where each borehole is a column of its layers with DIN 4023 hatching and colours, or as a side view along a drawn line with predicted layers between the boreholes), searches them (name, place, date with autocompletion), draws each borehole as a DIN 4023 profile column next to its source document, and lets users upload reports, configure and watch pipeline runs (retrying a whole run or a single failed extract/transform/validate job) and review the results.

## Review

The review page of a borehole (`/borehole/[id]/review`) is also its editing page ([ADR-0006](../docs/adr/0006-validation-stage-and-human-review.md)):

- One scrollable column on the left (core data in groups, then the layers as cards beside the sticky DIN 4023 profile) and the document on the right, with a draggable splitter (position kept in local storage, arrow keys move it). The document shown first is the borehole's own log split out by the pipeline; the original stays selectable.
- Values are edited in place; Enter or Tab saves and moves on, Escape restores. Saves use the API's answer instead of reloading the page, so the focus stays put; a green check confirms them. Numbers accept a decimal comma; invalid input is not saved. Coordinates are entered as x · y · EPSG (other systems are converted by the API); a map button shows the point.
- Open flags are shown under their field with "Looks right" (Ctrl+Enter) and, for a validator suggestion, "Apply …". The header counts resolved flags; once all are done "Verify & release" is offered, then "Next borehole →". `N` jumps to the next flag.
- Hover zoom: hovering a value, a layer or a layer in the profile zooms the document to where it is written (the page is drawn once at high resolution and moved with CSS transforms; the rest is dimmed); a focused field keeps its zoom, leaving the data zooms back out. Marks show validator corrections (blue) and human edits (violet) with history and undo.
- The sidebar's "Review" entry shows the number of unverified boreholes and opens the next one, most open flags first (`/review`).
- Before an extraction starts, `/upload/config` computes each file's SHA-256 in the browser and asks the API whether it was processed before; such files are skipped unless "Process again anyway" is ticked.

## Development setup

Prerequisites: Node.js ≥ 22.13 (`.nvmrc`), [pnpm](https://pnpm.io/) and the API running on `localhost:4000` (see [api/README.md](../api/README.md)); `API_INTERNAL_URL=http://localhost:4001 pnpm dev` uses another one, e.g. the Docker stack's. All data comes from the API; the Vite dev server proxies `/api` to it ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)).

```bash
cd web
pnpm install
pnpm dev        # http://localhost:5173

# Optional checks
pnpm check      # svelte-check
pnpm lint       # prettier + eslint
pnpm format
pnpm build      # production build (Node adapter)
```

The production build imports `../standards` (the DIN 4023 definitions), so the Docker image is built from the repo root. In production `API_INTERNAL_URL` tells the server where the API is. No test runner is configured.

## Technology

| Choice                                  | Why                                                                                                                                                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **SvelteKit 3 / Svelte 5 + TypeScript** | Little boilerplate and fast rendering for map- and chart-heavy pages; server hooks proxy the API so the browser only talks to one origin.                                                              |
| **MapLibre GL JS + supercluster**       | Open-source vector map that takes GeoJSON in WGS84 directly from the API, no API key, and clustering keeps large borehole sets responsive ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)). |
| **Own DIN 4023 engine in TypeScript**   | Profile columns follow the standard's materials, colours and hatching, rendered as SVG patterns from layer data ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)).                           |
| **pdf.js**                              | Shows the source document beside the profile so users can check the extraction.                                                                                                                        |
| **Tailwind 4 + Skeleton**               | Consistent styling and accessible components without a custom design system.                                                                                                                           |
| **Layered services/repositories**       | Keeps UI independent of the transport; mock repositories (faker) remain for offline UI work but are not wired in.                                                                                      |
| **adapter-node, pnpm**                  | Runs as a plain Node server in Docker; reproducible installs.                                                                                                                                          |

## Architecture

The frontend has three layers with one allowed direction of dependencies ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)):

```
UI (routes, components)  →  Service  →  Repository interface  →  ApiRepository (or MockRepository)
```

- **UI** (`src/routes`, `src/lib/components`) renders data and handles input. It imports only services and domain types, never repositories or `fetch`. ESLint enforces this.
- **Services** (`src/lib/services`) hold the use-case logic: ordering layers by depth, paging, turning a missing borehole into a `BoreholeNotFoundError`, running the search autocorrection. They depend on a repository _interface_, not on an implementation.
- **Repository interfaces** (`src/lib/repositories/*-repository.ts`) define what data access the app needs (boreholes, search, uploads, pipelines) and return domain types from `src/lib/domain`.
- **Repository implementations** (`repositories/api/`) call the Phoenix API and keep the wire types and the mapping to domain types to themselves, so API changes stay in one place. The faker-based implementations in `repositories/mock/` are kept for offline UI work but are not wired in ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)).
- **Dependency injection** happens in one composition root, `createServices({ fetch })` in `src/lib/services/index.ts`. It is the only place that knows which implementation is used: it builds the repositories with the API base URL and SvelteKit's `fetch` and injects them into the service constructors. Load functions call it and pass the results to pages, so swapping the data source means changing that one function, and services can be tested with a fake repository.
