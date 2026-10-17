---
id: ADR-0026
date: 2026-10-17
author: Kasimir Uihlein
title: Source documents may be shown in the application, but never published or committed
---

# ADR-0026 – Source documents may be shown in the application, but never published or committed

## Context

ADR-0014 said source documents must never be exposed via any API or frontend endpoint, and the pipeline doc repeated that the `documents` table is backend/review-only. The borehole detail page lists the original documents, though, and reviewers need to see the scan next to the extracted layers to check the extraction. The confidentiality concern is about the data leaving the team's environment (publishing, git, external services), not about the team's own application displaying it.

## Decision

This supersedes the "never exposed via any public API/frontend endpoint" part of ADR-0014. The storage layout of ADR-0014 (`priv/uploads/` inbox, `priv/storage/<document_id><ext>`) stays as it is.

- The API serves a document's file at `GET /api/documents/:id/file`, inline by default and as an attachment with `?download=1`. Responses carry `Cache-Control: private, no-store` and `X-Robots-Tag: noindex`.
- Only plain file names directly inside the storage directory are served; a `storage_path` with a directory part (e.g. mock data's `mock/…`) or `..` returns 404.
- `storage_path` and `raw_extraction` are still never part of any JSON response. The detail endpoint only adds `has_file` per document.
- The web app links the document name (opens in a new tab) and the "Download" menu entry to that endpoint.
- Unchanged: source documents must never be published, committed to git, or sent to external services. The files stay outside `priv/static`.

## Pros

- Reviewers can compare a log with its extracted data in one place.
- Documents are served by id only, so storage paths and file names on disk stay internal.

## Cons

- Anyone who can reach the API can read the documents. There is no authentication yet, so the API must stay on the local machine or a trusted network.
- Files leave the backend in browsers' memory and downloads; the rule against publishing them now relies on the people using the application.

## Alternatives

- Keep documents backend-only (ADR-0014): safe, but reviewers would have to find files on disk by id.
- Serve only rendered page images or previews: less data exposed, but more work and still the same content.
- Add authentication first: right for anything beyond the hackathon, too much for the prototype.

## Consequences

- Authentication is needed before the API is reachable by anyone outside the team.
- `docs/api-reference.md` and `docs/elixir-backend-borehole-pipeline.md` describe the new endpoint and rule.

## References

- ADR-0014, ADR-0025
- docs/api-reference.md
