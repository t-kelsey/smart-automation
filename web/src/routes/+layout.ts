import { createServices } from '#lib/services/index.ts';
import type { LayoutLoad } from './$types';

/** Number of boreholes still to review, for the sidebar badge; reloaded after a release. */
export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:review-count');
	try {
		const { boreholes } = await createServices({ fetch });
		return { reviewCount: (await boreholes.nextToReview()).total };
	} catch {
		return { reviewCount: null }; // the badge is not worth an error page
	}
};
