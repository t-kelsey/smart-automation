import { RepositoryError, createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

const toInt = (value: string | null) =>
	value ? Number.parseInt(value, 10) || undefined : undefined;

export const load: PageLoad = async ({ url, fetch }) => {
	const page = toInt(url.searchParams.get('page')) ?? 1;
	const pageSize = toInt(url.searchParams.get('pageSize')) ?? 10;
	try {
		const { boreholes } = await createServices({ fetch });
		return { result: await boreholes.list({ page, pageSize }), loadError: undefined };
	} catch (e) {
		if (!(e instanceof RepositoryError)) throw e;
		// Keep the page layout; the page shows the failure as a toast.
		return {
			result: {
				items: [],
				total: 0,
				page,
				pageSize,
				pageCount: 1,
				hasPrevious: false,
				hasNext: false
			},
			loadError: e
		};
	}
};
