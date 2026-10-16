---
id: ADR-0006
date: 2026-10-16
author: Tyler Kelsey
title: Cache each pipeline stage's output as JSON on disk
---

# ADR-0006 – Cache each pipeline stage's output as JSON on disk

## Context

OCR and translation are slow. While we develop the pipeline it gets re-run often after small fixes to a later stage, and repeating OCR on every file each time wastes most of the run.

## Decision

Each stage writes its output to a gitignored cache directory (for example `bem/.cache/<stage>/<file-hash>.json`). On a re-run, a stage reuses the cached result when its input is unchanged. A `--no-cache` flag, or a `--from <stage>` flag, forces recomputation.

## Pros

- Fast iteration on later stages.
- Intermediate results can be inspected for debugging.

## Cons

- A stale cache can hide changes made to an earlier stage, unless that stage is rerun with `--from`.
- Cached files contain confidential data and must be deleted after the event, together with `data/`.

## Alternatives

- No caching: simpler, but every run pays the full OCR and translation cost.

## Consequences

- The cache directory must be in `.gitignore`.
- `bem/main.py` needs the cache and `--from` handling.

## References

- ADR-0001
