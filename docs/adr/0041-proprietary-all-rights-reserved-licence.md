---
id: ADR-0041
date: 2026-10-18
author: ku
title: Proprietary "all rights reserved" licence
---

# ADR-0041 – Proprietary "all rights reserved" licence

## Context

The team wants all code owned equally by the team members and wants to keep the option of commercialising the project later. The borehole data in `data/` and all dependencies are owned by third parties. Co-authors hold joint copyright (in Germany § 8 UrhG), so exploiting or licensing the work requires everyone's consent.

## Decision

Publish no open-source licence. The root `LICENSE` file states "all rights reserved", names the five contributors as equal joint copyright holders, and permits viewing only for hackathon evaluation. It explicitly excludes `data/` and third-party dependencies from its scope.

## Pros

- Every future option stays open: relicense as open source, dual-license, sell, or use as a startup base.
- No irrevocable grant: permissive and copyleft licences cannot be withdrawn for copies already distributed.
- Matches the confidential-data constraints.

## Cons

- Nobody outside the team may legally reuse or contribute to the code, which reduces the project's reach.
- Judges and others need explicit permission for any use beyond viewing.
- Joint ownership means every future licensing or sale decision needs all five owners.

## Alternatives

- Apache-2.0 / MIT: maximum reuse, but irrevocable and gives up commercial exclusivity.
- AGPL-3.0: keeps the code open but deters closed-source use. It still cannot be undone, though the owners could later dual-license.
- PolyForm Noncommercial / BSL: source-available with commercial restrictions. Possible later step if the project is published.

## Consequences

- Add a short written co-ownership agreement (decision rules, exits, revenue split) before commercialising.
- Check the hackathon/organiser terms for any IP assignment or licence to the organiser, which would override this.
- Parts of the code written with AI assistance may not be protected by copyright, so exclusive rights over those parts are not guaranteed.
- Keep third-party licence notices when distributing builds.

## References

- `LICENSE`
- CLAUDE.md (data confidentiality)
