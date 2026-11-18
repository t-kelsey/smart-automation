import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

/** Opens the review of the next unverified borehole (most open flags first), if there is one. */
export const load: PageLoad = async ({ fetch }) => {
	const { boreholes } = await createServices({ fetch });
	const { next } = await boreholes.nextToReview();
	if (next) redirect(307, resolve('/borehole/[id]/review', { id: next.id }));
	return {};
};
