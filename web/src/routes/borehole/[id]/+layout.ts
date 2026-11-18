import { error } from '@sveltejs/kit';
import { BoreholeNotFoundError, createServices } from '#lib/services/index.ts';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ params, fetch, depends }) => {
	// Invalidated after every save on the review page, so the data never goes stale behind it.
	depends('app:borehole');
	const { boreholes } = await createServices({ fetch });
	try {
		return { borehole: await boreholes.getById(params.id) };
	} catch (e) {
		if (e instanceof BoreholeNotFoundError) error(404, 'Borehole not found');
		throw e;
	}
};
