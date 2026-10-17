import type { SearchHit } from '#lib/domain/borehole.ts';
import type { SearchRepository } from '#lib/repositories/search-repository.ts';
import { DEFAULT_PAGE_SIZE, type PagedResult } from './borehole-service';

export interface SearchRequest {
	q: string;
	/** 1-based page number. */
	page?: number;
	pageSize?: number;
}

/** Search use case. With the API repository the query is proxied to the API. */
export class SearchService {
	constructor(private readonly repository: SearchRepository) {}

	async search({
		q,
		page = 1,
		pageSize = DEFAULT_PAGE_SIZE
	}: SearchRequest): Promise<PagedResult<SearchHit>> {
		const size = Math.min(100, Math.max(1, Math.floor(pageSize)));
		const current = Math.max(1, Math.floor(page));
		const query = q.trim();
		// Do not hit the backend for an empty query.
		if (!query) {
			return {
				items: [],
				total: 0,
				page: 1,
				pageSize: size,
				pageCount: 1,
				hasPrevious: false,
				hasNext: false
			};
		}

		const result = await this.repository.search({
			q: query,
			limit: size,
			offset: (current - 1) * size
		});
		const pageCount = Math.max(1, Math.ceil(result.total / size));
		return {
			items: result.items,
			total: result.total,
			page: current,
			pageSize: size,
			pageCount,
			hasPrevious: current > 1,
			hasNext: current < pageCount
		};
	}
}
