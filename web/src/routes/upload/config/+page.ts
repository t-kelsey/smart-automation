import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { uploads, pipelines } = await createServices({ fetch });
	return { uploads, pipelines };
};
