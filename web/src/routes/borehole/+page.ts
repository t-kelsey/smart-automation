import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

const toInt = (value: string | null) =>
	value ? Number.parseInt(value, 10) || undefined : undefined;

export const load: PageLoad = async ({ url, fetch }) => {
	const { boreholes } = await createServices({ fetch });
	const result = await boreholes.list({
		page: toInt(url.searchParams.get('page')),
		pageSize: toInt(url.searchParams.get('pageSize')) ?? 10
	});
	return { result };
};
