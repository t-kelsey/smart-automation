import { error } from '@sveltejs/kit';
import { PipelineNotFoundError, createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { pipelines } = await createServices({ fetch });
	try {
		return { pipeline: await pipelines.get(params.id) };
	} catch (e) {
		if (e instanceof PipelineNotFoundError) error(404, 'Pipeline not found');
		throw e;
	}
};
