import { error } from '@sveltejs/kit';
import { BoreholeNotFoundError, createServices } from '#lib/services/index.ts';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ params, fetch }) => {
	const { boreholes } = await createServices({ fetch });
	try {
		return { borehole: await boreholes.getById(params.id) };
	} catch (e) {
		if (e instanceof BoreholeNotFoundError) error(404, 'Borehole not found');
		throw e;
	}
};
