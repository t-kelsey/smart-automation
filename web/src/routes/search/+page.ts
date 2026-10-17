import {
	InvalidSearchQueryError,
	RepositoryError,
	createServices,
	type SearchResult
} from '#lib/services/index.ts';
import type { PageLoad } from './$types';

const toInt = (value: string | null) =>
	value ? Number.parseInt(value, 10) || undefined : undefined;

/**
 * `?q=` is the query, `?page=`/`?pageSize=` the page, and `?exact=1` turns autocorrection off
 * (used by "Search instead for …").
 */
export const load: PageLoad = async ({ url, fetch }) => {
	const q = url.searchParams.get('q') ?? '';
	const page = toInt(url.searchParams.get('page')) ?? 1;
	const pageSize = toInt(url.searchParams.get('pageSize')) ?? 20;
	const autocorrect = url.searchParams.get('exact') !== '1';
	const empty: SearchResult = {
		items: [],
		total: 0,
		page,
		pageSize,
		pageCount: 1,
		hasPrevious: false,
		hasNext: false,
		query: q
	};

	try {
		const { search } = await createServices({ fetch });
		const result = await search.search({ q, page, pageSize, autocorrect });
		return { q, result, queryError: undefined, loadError: undefined };
	} catch (e) {
		// Keep the page layout; the page shows an invalid query inline and other failures as a toast.
		if (e instanceof InvalidSearchQueryError) {
			return { q, result: empty, queryError: e.message, loadError: undefined };
		}
		if (e instanceof RepositoryError) {
			return { q, result: empty, queryError: undefined, loadError: e };
		}
		throw e;
	}
};
