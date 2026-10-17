import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { pipelines } = await createServices({ fetch });
	return { pipelines: await pipelines.list() };
};
