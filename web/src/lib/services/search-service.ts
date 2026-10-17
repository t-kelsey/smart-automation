import type { SearchHit, SearchPage } from '#lib/domain/borehole.ts';
import { RepositoryError } from '#lib/repositories/borehole-repository.ts';
import type { SearchRepository } from '#lib/repositories/search-repository.ts';
import { DEFAULT_PAGE_SIZE, type PagedResult } from './borehole-service';

export interface SearchRequest {
	/** Query in the search query language (see the help drawer on the search page). */
	q: string;
	/** 1-based page number. */
	page?: number;
	pageSize?: number;
	/** Search for the autocorrected query if `q` finds nothing. Defaults to `true`. */
	autocorrect?: boolean;
}

export interface SearchResult extends PagedResult<SearchHit> {
	/** The query the hits are for: the request's, or its autocorrection. */
	query: string;
	/** Set if the hits are for an autocorrected query: the query as it was typed. */
	correctedFrom?: string;
}

/** The query could not be parsed, e.g. `date:19x9`. The message says why. */
export class InvalidSearchQueryError extends Error {
	constructor(message: string) {
		super(message);
		this.name = 'InvalidSearchQueryError';
	}
}

/** Search use case. The API parses the query and runs it in the database (ADR-0042). */
export class SearchService {
	constructor(private readonly repository: SearchRepository) {}

	async search({
		q,
		page = 1,
		pageSize = DEFAULT_PAGE_SIZE,
		autocorrect = true
	}: SearchRequest): Promise<SearchResult> {
		const size = Math.min(100, Math.max(1, Math.floor(pageSize)));
		const current = Math.max(1, Math.floor(page));
		const query = q.trim();
		// Do not hit the backend for an empty query.
		if (!query) return this.paged({ items: [], total: 0 }, query, 1, size);

		const result = await this.fetch(query, current, size);
		// A misspelt query finds nothing: show the hits of its correction instead, if it has any.
		if (autocorrect && result.total === 0 && result.suggestion) {
			const corrected = await this.fetch(result.suggestion, current, size);
			if (corrected.total > 0) {
				return { ...this.paged(corrected, result.suggestion, current, size), correctedFrom: query };
			}
		}
		return this.paged(result, query, current, size);
	}

	private async fetch(q: string, page: number, size: number): Promise<SearchPage> {
		try {
			return await this.repository.search({ q, limit: size, offset: (page - 1) * size });
		} catch (e) {
			if (e instanceof RepositoryError && e.status === 400) {
				throw new InvalidSearchQueryError(e.detail ?? 'The search query is invalid.');
			}
			throw e;
		}
	}

	private paged(result: SearchPage, query: string, page: number, size: number): SearchResult {
		const pageCount = Math.max(1, Math.ceil(result.total / size));
		return {
			items: result.items,
			total: result.total,
			page,
			pageSize: size,
			pageCount,
			hasPrevious: page > 1,
			hasNext: page < pageCount,
			query
		};
	}
}
