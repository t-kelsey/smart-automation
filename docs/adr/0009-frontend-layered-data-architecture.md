---
id: ADR-0009
date: 2026-10-17
author: Kasimir Uihlein
title: Layered data architecture in the frontend (UI, service, repository)
---

# ADR-0009 – Layered data architecture in the frontend (UI, service, repository)

## Context

The SvelteKit frontend (`web/`) has no data layer. The borehole details page loaded a hardcoded object from a mock file next to the route. The Phoenix API has Ecto schemas for `Borehole`, `BoreholeLayer` and `Document` but no routes yet, and there is no live data. The frontend must be developed against mock data now and switch to the API later without changes in components.

The API entities differ from what the UI needs: snake_case fields, decimals, a PostGIS location, free-text `stratigraphy`/`petrography`/`color` on layers, and documents without type, size or language.

## Decision

Three layers with one allowed direction of dependencies:

```
UI (routes, components)  →  Service  →  Repository interface  →  MockRepository | ApiRepository
```

- **UI** (`src/routes`, `src/lib/components`) imports only services and domain types. It never imports repositories, `fetch` calls or mock data. An ESLint `no-restricted-imports` rule enforces this.
- **Services** (`src/lib/services`) are classes that take a repository in the constructor. They hold use-case logic (for example `BoreholeNotFoundError`, ordering layers by depth). `BoreholeService` is the first one.
- **Repositories** (`src/lib/repositories`) implement the `BoreholeRepository` interface. They return domain types (`src/lib/domain`), not wire DTOs.
  - `ApiBoreholeRepository` calls the Phoenix API. DTOs (`api-types.ts`) and mapping (`mappers.ts`) stay inside `repositories/api/`.
  - `MockBoreholeRepository` serves 20 deterministic boreholes with layers and documents from `mock-data.ts`, generated with `@faker-js/faker` (fixed seed). The first borehole is the former hand-written `BK 1042`.
- **Dependency injection** happens in one composition root, `createServices({ fetch })` in `src/lib/services/index.ts`. It picks the repository from `PUBLIC_DATA_SOURCE` (`mock` default, or `api`) and passes SvelteKit's `fetch` to the API repository. Load functions call it and hand data to pages. The repository modules are loaded with dynamic `import()`.
- **Env variables** are declared in `src/env.ts` (SvelteKit 3 `defineEnvVars`): `PUBLIC_DATA_SOURCE`, `PUBLIC_API_URL` (default `/api`, proxied to `localhost:4000` by the Vite dev server).

### Expected API contract (not implemented yet on the API side)

- `GET /api/boreholes?search&limit&offset` → `{ "data": [Borehole], "total": n }`
- `GET /api/boreholes/:id` → `{ "data": Borehole }` with `borehole_layers` and `document` embedded; `404` if unknown.
- `Borehole` uses the Ecto field names; `location` is a GeoJSON Point (`coordinates: [lon, lat]`).

### Mapping between API entities and domain types

| Domain | API |
|---|---|
| `cause` | `purpose` |
| `date` / `endDate` | `drilled_at` / `end_date` |
| `layer.startDepth` / `endDepth` | `depth_from_m` / `depth_to_m` |
| `layer.petrography.lithology` | keyword lookup in `petrography` (falls back to `unknown`) |
| `layer.stratigraphy` | first word of `stratigraphy` is the code, the rest the name |
| `layer.color` | hex if `color` is a hex string, otherwise grey with the raw text as name |
| `document.type` | file extension of `original_filename` |

Fields that the API does not have (`client`, `location.place`, document `pages`/`sizeKb`) are optional in the domain types, and the UI shows a dash or hides them.

## Pros

- Components do not change when the data source changes.
- The UI can be built and demoed without a running API or database.
- The repository interface is small, so tests can use any fake implementation.
- Wire-format knowledge lives in one folder.
- The lint rule makes the layering checkable.

## Cons

- More files and indirection for a small app. The service layer is thin today.
- Mappers must follow API changes by hand; nothing checks the DTOs against the Ecto schemas.
- Best-effort parsing of free-text layer fields (lithology, colour, stratigraphy) is lossy until the API normalises them.
- The mock data is invented and may hide real data problems (missing depths, odd units).

## Alternatives

- **`fetch` directly in load functions:** least code, but mock/API switching and the data mapping end up in every route.
- **Context-based DI (Svelte `setContext`):** useful in components, but load functions run outside the component tree, so a plain factory is simpler.
- **A DI container library:** unnecessary for two implementations of one interface.
- **Global store as data layer:** mixes caching and UI state; can be added inside a service later.
- **Repositories returning raw DTOs, services mapping:** puts wire knowledge in the service layer and makes mock data snake_case too.

## Consequences

- New data access goes through the pattern: domain type → repository method (interface, mock, API) → service method → load function.
- The API needs to provide the endpoints above, plus `client`, a place name and document metadata, or the UI keeps showing gaps.
- `elevation` is nullable in the domain because the API field is optional. The cross-section currently falls back to 0 when it is missing.
- Write operations (edit page, document upload) will extend the repository interface later.

## References

- ADR-0001, ADR-0005
- `api/lib/api/boreholes/` (Ecto schemas)
- SvelteKit environment variables (https://svelte.dev/docs/kit/environment-variables)
