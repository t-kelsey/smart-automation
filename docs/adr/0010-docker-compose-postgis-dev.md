---
id: ADR-0010
date: 2026-10-17
author: jl
title: Local Postgres+PostGIS via Docker Compose for development
---

# ADR-0010 – Local Postgres+PostGIS via Docker Compose for development

## Context

`api/` needs Postgres with the PostGIS extension for the `boreholes.location` geometry column. Requiring every contributor to install PostGIS locally is heavy, platform-dependent, and in practice broke: the official `postgis/postgis` Docker image only ships `amd64` manifests (no Apple Silicon support), and a local Homebrew `postgresql@14` install was missing the `postgis` extension control file and additionally conflicted with the container on port 5432 (bound to `127.0.0.1`, taking priority over the container's wildcard bind for `localhost` connections).

## Decision

Add a root-level `docker-compose.yml` running `imresamu/postgis` (a multi-arch fork of `postgis/postgis`) on `localhost:5432`, with credentials matching `api/config/dev.exs`/`test.exs` (`postgres`/`postgres`, database `api_dev`).

## Pros

- No local Postgres/PostGIS installation needed for any contributor.
- Works natively on both Apple Silicon and amd64 machines.
- Credentials are the Phoenix-generator defaults already committed in `config/dev.exs`/`test.exs` — nothing new to leak.

## Cons

- Requires Docker Desktop (or compatible) running locally.
- Any pre-existing local Postgres service bound to port 5432 must be stopped first, or the app silently connects to the wrong database.

## Alternatives

- Official `postgis/postgis` image — rejected, no arm64 manifest, fails to pull on Apple Silicon.
- Local Homebrew install of `postgresql` + `postgis` — rejected, platform-specific setup burden, and the extension control file was missing/misconfigured in practice.

## Consequences

- `README.md` documents `docker compose up -d` as the required first step, and calls out stopping a local Postgres service if one is already running on port 5432.

## References

- README.md
- docker-compose.yml
