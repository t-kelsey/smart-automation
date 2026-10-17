import type { Page, SearchHit, SearchQuery } from '#lib/domain/borehole.ts';

/** Full-text search over boreholes and their extracted content. */
export interface SearchRepository {
	search(query: SearchQuery): Promise<Page<SearchHit>>;
}
