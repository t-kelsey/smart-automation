# web

Web frontend of the geodatabase: explore, search and review boreholes and start the extraction pipeline.

## Why it exists

The extracted data is only useful if people can find and judge it. The web app shows boreholes on an interactive world map, searches them (name, place, date with autocompletion), draws each borehole as a DIN 4023 profile column next to its source document, and lets users upload reports, configure and watch pipeline runs (retrying a whole run or a single failed extract/transform job) and review the results.

## Development setup

Prerequisites: Node.js ≥ 22.13 (`.nvmrc`), [pnpm](https://pnpm.io/) and the API running on `localhost:4000` (see [api/README.md](../api/README.md)). All data comes from the API; the Vite dev server proxies `/api` to it ([ADR-0029](../docs/adr/0029-web-uses-api-only.md)).

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

| Choice                                  | Why                                                                                                                                                                                                      |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SvelteKit 3 / Svelte 5 + TypeScript** | Little boilerplate and fast rendering for map- and chart-heavy pages; server hooks proxy the API so the browser only talks to one origin.                                                                |
| **MapLibre GL JS + supercluster**       | Open-source vector map that takes GeoJSON in WGS84 directly from the API, no API key, and clustering keeps large borehole sets responsive ([ADR-0010](../docs/adr/0010-sveltekit-maplibre-frontend.md)). |
| **Own DIN 4023 engine in TypeScript**   | Profile columns follow the standard's materials, colours and hatching, rendered as SVG patterns from layer data ([ADR-0021](../docs/adr/0021-din-4023-borehole-drawing.md)).                             |
| **pdf.js**                              | Shows the source document beside the profile so users can check the extraction.                                                                                                                          |
| **Tailwind 4 + Skeleton**               | Consistent styling and accessible components without a custom design system.                                                                                                                             |
| **Layered services/repositories**       | Keeps UI independent of the transport; mock repositories (faker) remain for offline UI work but are not wired in.                                                                                        |
| **adapter-node, pnpm**                  | Runs as a plain Node server in Docker; reproducible installs.                                                                                                                                            |

## Architecture

The frontend has three layers with one allowed direction of dependencies ([ADR-0009](../docs/adr/0009-frontend-layered-data-architecture.md)):

```
UI (routes, components)  →  Service  →  Repository interface  →  ApiRepository (or MockRepository)
```

- **UI** (`src/routes`, `src/lib/components`) renders data and handles input. It imports only services and domain types, never repositories or `fetch`. ESLint enforces this.
- **Services** (`src/lib/services`) hold the use-case logic: ordering layers by depth, paging, turning a missing borehole into a `BoreholeNotFoundError`, running the search autocorrection. They depend on a repository _interface_, not on an implementation.
- **Repository interfaces** (`src/lib/repositories/*-repository.ts`) define what data access the app needs (boreholes, search, uploads, pipelines) and return domain types from `src/lib/domain`.
- **Repository implementations** (`repositories/api/`) call the Phoenix API and keep the wire types and the mapping to domain types to themselves, so API changes stay in one place. The faker-based implementations in `repositories/mock/` are kept for offline UI work but are not wired in ([ADR-0029](../docs/adr/0029-web-uses-api-only.md)).
- **Dependency injection** happens in one composition root, `createServices({ fetch })` in `src/lib/services/index.ts`. It is the only place that knows which implementation is used: it builds the repositories with the API base URL and SvelteKit's `fetch` and injects them into the service constructors. Load functions call it and pass the results to pages, so swapping the data source means changing that one function, and services can be tested with a fake repository.
