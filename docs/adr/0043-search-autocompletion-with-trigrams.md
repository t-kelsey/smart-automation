---
id: ADR-0043
date: 2026-10-18
author: Kasimir Uihlein
title: Search autocompletion while typing with trigram (q-gram) matching in the database
---

# ADR-0043 – Search autocompletion while typing with trigram (q-gram) matching in the database

## Context

The search query language (ADR-0042) finds boreholes by name, place and date, and autocorrects a query that finds nothing. While typing, users still have to know how a place or borehole is spelt in the data (e.g. `MARRUECOS`, `B 1/59 Schönberg`), and they only learn about a typo after searching.

## Decision

- **Endpoint `GET /api/boreholes/complete?q=&limit=`** returns completions `{value, kind, query}` for the term at the end of `q`. `query` is the whole query with that term completed (quoted if needed, followed by a space), so the client only replaces the input.
- **The parser finds the term being typed.** `SearchQuery.completion_targets/1` splits off the last term (outside quotes), keeps its `-`, key and earlier comma alternatives, and decides what to complete: keys for a bare word (`pla` → `place:`), names and places for a bare word, names for `name:`, places for `place:`; nothing for dates, unknown keys or after a trailing space.
- **Trigram (q-gram, q = 3) matching in Postgres.** Candidates are values that contain the text (`ILIKE`) or are similar to it (`<%`, word similarity ≥ pg_trgm's default 0.6), both served by the GIN trigram indexes of ADR-0042. They are ranked: value starts with the text, a word starts with it, contains it, then by `word_similarity`, length and name. A typo with one missing or extra letter still completes.
- **Web.** `SearchBar.svelte` uses Skeleton's Combobox with the completions as its collection, debounced (120 ms) and dropping stale answers. Arrow keys and Enter pick a completion; Enter without one searches. The bar is a rounded pill, like the sidebar.

## Pros

- Users see how values are spelt in the data and fix typos before searching.
- No new index or table: the trigram indexes of ADR-0042 serve both search and completion.
- The query string stays the only state; the API returns finished queries, so the client has no parsing logic.

## Cons

- One request per pause in typing.
- Swapped letters inside a word (`Marsielle`) fall below the 0.6 threshold; only the autocorrection on search (threshold 0.3) catches them.
- Values shorter than 2 characters and dates are not completed.
- Completing whole values: long names fill the dropdown when many boreholes share a word (e.g. a city name).

## Alternatives

- **Completing in the browser from a downloaded vocabulary:** no requests while typing, but the list grows with the data and duplicates the parser.
- **A separate word table with prefix (B-tree) lookups:** faster for pure prefixes, but no typo tolerance and needs maintaining on every insert.
- **A lower similarity threshold (0.5):** catches more typos, but short inputs then match unrelated values (`MAR` → `Madrid`).

## Consequences

- `docs/api-reference.md` documents `GET /api/boreholes/complete`; the route sits before `/boreholes/:id`.
- The search page's help drawer mentions the completions.

## References

- ADR-0042
- `api/lib/api/boreholes/search_query.ex` (`completion_targets/1`, `complete/2`), `Api.Boreholes.complete_query/2`
- `web/src/lib/components/search/SearchBar.svelte`
