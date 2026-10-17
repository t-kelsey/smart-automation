import type { SearchCompletion, SearchPage, SearchQuery } from '#lib/domain/borehole.ts';

/** Search over boreholes. An invalid query rejects with a `RepositoryError` with status 400. */
export interface SearchRepository {
	search(query: SearchQuery): Promise<SearchPage>;
	/** Completions for the term being typed at the end of `q`, best first. */
	complete(q: string, limit: number): Promise<SearchCompletion[]>;
}
