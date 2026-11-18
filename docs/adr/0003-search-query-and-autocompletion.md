---
id: ADR-0003
date: 2026-11-18
author: Tyler Kelsey
title: Search query language, autocorrection and autocompletion in the database with trigram indexes
---

# ADR-0003 – Search query language, autocorrection and autocompletion in the database with trigram indexes

## Context

Users look for a borehole log by its name, the place it was drilled and when. A single substring match over every field was slow to reason about, had no indexes, could not express dates, and returned nothing for a typo. Users also need to see how places and names are spelt in the data while they type.

## Decision

**Query language.** `Api.Boreholes.SearchQuery` parses `q` into terms that must all match:

- Bare words and `"phrases"` match name, external id or place.
- `name:`, `place:` (aliases `location:`, `loc:`).
- `date:` with a year, a date (`1959-06-12` or `12.06.1959`), a range (`1950..1960`, open at either end) or a comparison (`>`, `>=`, `<`, `<=`); `after:` and `before:` as well. A bare year, date or range is a date term.
- Comma alternatives (`place:Bern,Basel`) and negation (`-place:Bern`).
- Invalid dates return `400` with a readable `detail`.

**In the database.** Terms become Ecto `dynamic` conditions: `ILIKE` on name, external id and place, range comparisons on `drilled_at`. The score is a SQL expression (name 10, external id 8, place 5, +5 for a name prefix). Filtering, ranking and paging all run in Postgres.

**Indexes.** GIN trigram indexes (`pg_trgm`) on `boreholes.name`, `external_id` and `place`; a B-tree on `drilled_at`.

**Autocorrection.** When a search finds nothing, the response carries `suggestion`. Unknown keys become the closest key (Jaro distance). Each unquoted, non-negated text value of at least three characters that matches nothing is replaced by the most similar word from its columns. Candidate rows come from the trigram index (word similarity ≥ 0.4); words are ranked by `similarity()` (≥ 0.3). The web shows "Showing results for…" and offers the original query; `?exact=1` turns this off.

**Autocompletion.** `GET /api/boreholes/complete?q=&limit=` returns `{value, kind, query}` for the term at the end of `q`. `query` is the complete query with that term replaced, so the client only swaps the input. For a bare word it offers keys (`pla` → `place:`) and names or places; for `name:` names, for `place:` places. Nothing is offered for dates, unknown keys, values under 2 characters or after a trailing space. Candidates are values containing the text (`ILIKE`) or similar to it (word similarity ≥ 0.6, so one missing or extra letter still matches), ranked: starts with the text, a word starts with it, contains it, then by similarity, length and name. The web uses a debounced (120 ms) combobox; stale answers are dropped.

**Scope.** Layer text, `purpose` and `client` are not searched. Results have no snippets.

## Pros

- Precise searches such as `place:Stuttgart 1950..1960` instead of one substring over everything.
- Trigram indexes keep substring search fast beyond the 10 000-row prototype cap.
- Autocorrection and completion need no dictionary or extra service; the data is the vocabulary.
- One parser in the backend; the web passes the string through and shows errors.
- Search and completion share the same indexes.

## Cons

- Users must learn the syntax beyond bare words (the help drawer on the search page explains it).
- A bare four-digit number is always a date; a name containing a year needs quotes.
- No accent folding: `Schonberg` finds `Schönberg` only through autocorrection.
- Terms under three characters cannot use the trigram index.
- Swapped letters inside a word fall below the completion threshold; only search-time autocorrection (0.3) catches them.
- Long names fill the dropdown when many boreholes share a word.
- Layer descriptions (e.g. "Gipskeuper") cannot be searched.

## Alternatives

- **Postgres full-text search (`tsvector`):** needs a language configuration per log language and does not match substrings such as "B 1/59".
- **Parse the query in the web app:** every client would need its own parser, and the API would have no text search.
- **Structured parameters only (`place=`, `drilled_from=`):** these exist on `/boreholes`, but a single search box with a short syntax is quicker to use.
- **Fuzzy matching over a word table (Levenshtein):** needs a maintained word table; trigram similarity over indexed columns needs nothing extra.
- **Browser-side completion from a downloaded vocabulary:** the list grows with the data and duplicates the parser.
- **Separate prefix (B-tree) word table for completion:** fast, but no typo tolerance and it must be maintained on every insert.
- **Lower similarity threshold (0.5) for completion:** catches more typos, but short inputs then match unrelated values (`MAR` → `Madrid`).

## Consequences

- `q` on `GET /api/boreholes` and `/api/boreholes/search` uses this language; `snippet` is gone and `suggestion` is new.
- A future `layer:` key would extend the same language if layer text is ever searched.

## References

- ADR-0001 (read API)
- `docs/api-reference.md` ("Search query language")
- `api/lib/api/boreholes/search_query.ex` (`completion_targets/1`, `complete/2`)
- `web/src/lib/components/search/SearchBar.svelte`, `SearchHelpDrawer.svelte`
