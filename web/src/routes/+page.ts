import type { BoreholeSummary } from '#lib/domain/borehole.ts';
import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { boreholes } = await createServices({ fetch });
	// The service caps the page size, so collect all pages for the map and the stats.
	const all: BoreholeSummary[] = [];
	for (let page = 1; ; page++) {
		const result = await boreholes.list({ page, pageSize: 100 });
		all.push(...result.items);
		if (!result.hasNext) break;
	}
	return { boreholes: all };
};
