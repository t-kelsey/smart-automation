# web

Web frontend of the geodatabase: explore, search and review boreholes and start the extraction pipeline.

## Why it exists

The extracted data is only useful if people can find and judge it. The web app shows boreholes on an interactive world map, searches them (name, place, date with autocompletion), draws each borehole as a DIN 4023 profile column next to its source document, and lets users upload reports, configure and watch pipeline runs (retrying a whole run or a single failed extract/transform/validate job) and review the results.

## Review

The review page of a borehole (`/borehole/[id]/review`) is also its editing page ([ADR-0006](../docs/adr/0006-validation-stage-and-human-review.md)):

- Core data and layers are edited in place (saved on Enter or blur, Escape cancels); layers can be added and deleted, petrography is picked from the DIN 4023 terms, coordinates are entered as x/y/EPSG.
- Marks per value: yellow/red for open warnings/errors ("Looks right" resolves them), blue for a validator correction, violet for a human edit; ↶ undoes the last change, the popover lists the history with "Restore". Deleted layers are listed below the table.
- Hovering a value, a layer row or a layer in the profile shows where it is written in the document (page and box). "Next flag" walks the open flags; "Verify & release" sets the borehole verified.
- Lists show the open flags and can sort by them; the map draws verified boreholes filled and unverified ones hollow.

## Development setup

Prerequisites: Node.js ≥ 22.13 (`.nvmrc`), [pnpm](https://pnpm.io/) and the API running on `localhost:4000` (see [api/README.md](../api/README.md)). All data comes from the API; the Vite dev server proxies `/api` to it ([ADR-0004](../docs/adr/0004-web-frontend-and-din-4023.md)).

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
