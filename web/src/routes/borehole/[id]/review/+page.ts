import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

/** The borehole comes from the layout; the page also needs the service for its edits. */
export const load: PageLoad = async ({ fetch }) => {
	const { boreholes } = await createServices({ fetch });
	return { service: boreholes };
};
