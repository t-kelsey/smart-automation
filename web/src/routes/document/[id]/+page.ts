import { error } from '@sveltejs/kit';
import { DocumentNotFoundError, createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { boreholes } = await createServices({ fetch });
	try {
		return { document: await boreholes.getDocument(params.id) };
	} catch (e) {
		if (e instanceof DocumentNotFoundError) error(404, 'Document not found');
		throw e;
	}
};
