---
id: ADR-0005
date: 2026-11-18
author: Tyler Kelsey
title: Local PostGIS through Docker Compose and an all-rights-reserved licence
---

# ADR-0005 – Local PostGIS through Docker Compose and an all-rights-reserved licence

## Context

**Database.** `api/` needs Postgres with PostGIS for the `boreholes.location` column. Requiring each contributor to install PostGIS locally is platform-dependent and was already failing: the official `postgis/postgis` image has no arm64 build, and a local Homebrew Postgres lacked the PostGIS extension and clashed with the container on port 5432.

**Licence.** The team wants all code owned equally by its five members and keeps the option of commercialising the project. The borehole data in `data/` and all dependencies belong to third parties. Co-authors hold joint copyright (§ 8 UrhG), so any exploitation or licensing needs everyone's consent.

## Decision

**Local database.** The root `docker-compose.yml` runs `imresamu/postgis` (a multi-arch fork of `postgis/postgis`) on `localhost:5432` with the Phoenix-generator credentials already in `config/dev.exs` and `config/test.exs` (`postgres`/`postgres`, database `api_dev`). `docker compose up -d db` is the first step; the full stack runs with `docker compose up --build`. Credentials are development defaults and nothing sensitive is stored.

**Licence.** No open-source licence. The root `LICENSE` states "all rights reserved", names the five contributors as equal joint copyright holders, and permits viewing for hackathon evaluation only. Its scope excludes `data/` and third-party dependencies.

## Pros

- Works on both Apple Silicon and amd64 with no local PostGIS install.
- Uses credentials that are already committed as defaults, so nothing new leaks.
- Every future licensing option stays open: open source, dual licence, sale, or a startup base.
- Permissive and copyleft licences cannot be withdrawn for copies already distributed; this one can change.
- Matches the confidentiality constraints for the data.

## Cons

- Docker Desktop (or a compatible runtime) must be running.
- A local Postgres on port 5432 must be stopped first, or the app silently connects to the wrong database.
- Nobody outside the team may legally reuse or contribute to the code, which limits reach.
- Judges and others need explicit permission for any use beyond viewing.
- Every future licensing or sale decision needs all five owners.
- Code written with AI assistance may not be protected by copyright, so exclusive rights over those parts are not guaranteed.

## Alternatives

- **Official `postgis/postgis` image:** rejected; no arm64 manifest.
- **Local Homebrew Postgres with PostGIS:** rejected; platform-specific setup and a missing extension control file in practice.
- **Apache-2.0 or MIT:** maximum reuse, but irrevocable and gives up commercial exclusivity.
- **AGPL-3.0:** keeps the code open but deters closed-source use; still irrevocable, although the owners could later dual-license.
- **PolyForm Noncommercial or BSL:** source-available with commercial limits; a possible later step if the project is published.

## Consequences

- `README.md` documents `docker compose up -d` as the first step and the need to stop a local Postgres on port 5432.
- Before commercialising, a written co-ownership agreement (decision rules, exits, revenue split) is needed.
- The hackathon or organiser terms must be checked for any IP assignment or licence to the organiser, which would override this licence.
- Third-party licence notices must be kept when builds are distributed.

## References

- `docker-compose.yml`, `README.md`
- `LICENSE`
- `CLAUDE.md` (data confidentiality)
