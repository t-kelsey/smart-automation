import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { boreholes } = await createServices({ fetch });
	// Only the few rows the dashboard shows; the map loads its own points in the browser.
	const { items } = await boreholes.list({ pageSize: 8 });
	return { boreholes: items };
};
