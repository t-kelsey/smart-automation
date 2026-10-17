import type { Page, SearchHit, SearchQuery } from '#lib/domain/borehole.ts';
import { RepositoryError } from '../borehole-repository';
import type { SearchRepository } from '../search-repository';
import type { ApiListResponse, ApiSearchHit } from './api-types';
import { toSummary } from './mappers';

interface Options {
	baseUrl: string;
	fetch: typeof fetch;
}

/** Forwards search queries to the API's `GET /search` endpoint; ranking happens server-side. */
export class ApiSearchRepository implements SearchRepository {
	constructor(private readonly options: Options) {}

	async search({ q, limit, offset }: SearchQuery): Promise<Page<SearchHit>> {
		const query = new URLSearchParams({ q });
		if (limit !== undefined) query.set('limit', String(limit));
		if (offset !== undefined) query.set('offset', String(offset));
		const path = `/search?${query}`;

		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}${path}`, {
				headers: { accept: 'application/json' }
			});
		} catch (cause) {
			throw new RepositoryError(`API request failed: ${path}`, undefined, { cause });
		}
		if (!response.ok)
			throw new RepositoryError(`API ${path} returned ${response.status}`, response.status);

		const body = (await response.json()) as ApiListResponse<ApiSearchHit>;
		return {
			items: body.data.map((hit) => ({
				borehole: toSummary(hit.borehole),
				score: hit.score,
				snippet: hit.snippet ?? undefined
			})),
			total: body.total
		};
	}
}
