import { resolve } from '$app/paths';
import type { ResolvedPathname } from '$app/types';

/** Link to the search page for `q`; `exact` turns autocorrection off. */
export function searchHref(
	q: string,
	{ exact = false, page = 1, pageSize = 0 } = {}
): ResolvedPathname {
	const params = new URLSearchParams({ q });
	if (exact) params.set('exact', '1');
	if (page > 1) params.set('page', String(page));
	if (pageSize) params.set('pageSize', String(pageSize));
	// Only the query string is added to the resolved path.
	return `${resolve('/search')}?${params}` as ResolvedPathname;
}
