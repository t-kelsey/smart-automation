import { RepositoryError, createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:pipelines');
	const { pipelines } = await createServices({ fetch });
	try {
		return { pipelines: await pipelines.list(), loadError: undefined, service: pipelines };
	} catch (e) {
		if (!(e instanceof RepositoryError)) throw e;
		// Keep the page layout; the page shows the failure as a toast.
		return { pipelines: [], loadError: e, service: pipelines };
	}
};
