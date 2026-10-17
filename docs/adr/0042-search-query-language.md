---
id: ADR-0042
date: 2026-10-18
author: Kasimir Uihlein
title: Search query language over name, place and date, run in the database with trigram indexes and autocorrection
---

# ADR-0042 – Search query language over name, place and date, run in the database with trigram indexes and autocorrection

## Context

The search page was a placeholder. The API's `q` (ADR-0025) was a single `ILIKE` substring over many borehole and layer fields, without indexes, without dates and without a way to say which field a word is meant for. Users look for a log by its name, the place it was drilled and when; a typo returned nothing.

## Decision

- **A small query language, parsed in the API.** `Api.Boreholes.SearchQuery` parses `q` into terms that must all match: bare words and `"phrases"` (name, external id or place), `name:`, `place:` (`location:`, `loc:`), `date:` with a year, month, day (`1959-06-12` or `12.06.1959`), a range (`1950..1960`, open on either side) or a comparison (`>`, `>=`, `<`, `<=`), `after:`/`before:`, comma alternatives (`place:Bern,Basel`) and negation (`-place:Bern`). A bare year, date or range is a date term. Invalid dates return `400` with a readable `detail`. The full syntax is in `docs/api-reference.md` and in the help drawer on the search page.
- **Runs in the database.** Terms become Ecto `dynamic` conditions (`ILIKE` on `name`/`external_id`/`place`, range comparisons on `drilled_at`), the score is a SQL expression (name 10, external id 8, place 5, +5 for a name prefix), so filtering, ranking and paging all happen in Postgres.
- **Indexes.** `pg_trgm` GIN indexes on `boreholes.name`, `external_id` and `place` serve `ILIKE '%term%'` and the similarity lookups; a B-tree on `drilled_at` serves date ranges.
- **Autocorrection.** When a search finds nothing, the API returns `suggestion`: unknown keys become the closest key (Jaro distance), and each unquoted, non-negated text value (≥ 3 characters) that occurs nowhere is replaced by the most similar word of its columns. Candidate rows come from the trigram index (`<%`, word similarity ≥ 0.4), their words are ranked by `similarity()` (≥ 0.3). The web's `SearchService` runs the suggestion and shows "Showing results for … / Search instead for …" (`?exact=1` turns it off).
- **Scope.** Layer text, `purpose` and `client` are no longer searched; there is no snippet any more.

## Pros

- Precise searches (`place:Stuttgart 1950..1960`) instead of one substring over everything.
- Substring search stays fast beyond the 10 000-row prototype cap thanks to the trigram indexes.
- Autocorrection needs no extra dictionary or service: the data itself is the vocabulary.
- One parser in the backend; the web only passes the string through and shows `detail` on errors.

## Cons

- Users have to learn the syntax for anything beyond bare words (mitigated by the help drawer and examples).
- Bare 4-digit numbers are dates; a name containing "1959" needs quotes.
- No accent folding: `Schonberg` finds `Schönberg` only through autocorrection.
- Terms shorter than 3 characters cannot use the trigram index.
- Searching layer descriptions (e.g. "Gipskeuper") is no longer possible.

## Alternatives

- **Postgres full-text search (`tsvector`)**: stemming and ranking, but needs a language configuration per log language and does not do substrings of names like "B 1/59".
- **Parsing the query in the web app** and sending structured filters: the API would stay simpler, but every client would need its own parser and the API would have no text search for other consumers.
- **Separate structured parameters only** (`place=`, `drilled_from=`): already exist on `/boreholes`; a single search box with a short syntax is quicker to use.
- **A spelling dictionary (e.g. `fuzzystrmatch`/Levenshtein over a word table)**: needs a maintained word table; trigram similarity over the indexed columns needs nothing extra.

## Consequences

- `q` on `GET /api/boreholes` and `/api/boreholes/search` uses the language; `snippet` is gone from the response, `suggestion` is new.
- ADR-0025's "ranked search with `ILIKE`" is replaced by this ADR.
- Searching layer content would be a new key (e.g. `layer:`) in the same language.

## References

- ADR-0009, ADR-0025
- docs/api-reference.md (Search query language)
- `api/lib/api/boreholes/search_query.ex`, `api/lib/api/boreholes.ex`
- `web/src/routes/search/`, `web/src/lib/components/search/SearchHelpDrawer.svelte`
