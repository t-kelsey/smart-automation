---
id: ADR-0010
date: 2026-10-17
author: jl
title: Frontend stack - SvelteKit app with MapLibre for the interactive map
---

# ADR-0010 – Frontend stack - SvelteKit app with MapLibre for the interactive map

## Context

`web/` was already scaffolded as a SvelteKit 3 / Svelte 5 app before this decision. The challenge requires an interactive world map that renders georeferenced boreholes and their detail view (profile column, stratigraphy table, metadata).

## Decision

Use the existing SvelteKit app as the frontend, with MapLibre GL JS for the interactive map. The map consumes GeoJSON directly from the Phoenix API (see ADR-0012); MapLibre and GeoJSON both use WGS84 lon/lat, so no coordinate conversion is needed in the frontend.

## Pros

- No new project scaffolding needed — `web/` already exists and matches this choice.
- MapLibre is open-source and needs no API key/billing, unlike Mapbox GL JS.
- GeoJSON `FeatureCollection` output maps directly onto MapLibre sources.

## Cons

- Contributors need to be comfortable with Svelte 5 runes mode and the project's `web/AGENTS.md` conventions (Svelte MCP tools).
- MapLibre has a smaller ecosystem/tooling surface than Mapbox or Google Maps.

## Alternatives

- Mapbox GL JS: proprietary, requires an API key and billing account — rejected.
- Leaflet: simpler API, but weaker performance for larger vector datasets.
- A different frontend framework (React, etc.): would discard the already-scaffolded `web/` app for no clear benefit.

## Consequences

- The backend map/search API (see the Elixir backend task doc) must return `boreholes` as a GeoJSON `FeatureCollection` in WGS84.

## References

- docs/elixir-backend-borehole-pipeline.md
