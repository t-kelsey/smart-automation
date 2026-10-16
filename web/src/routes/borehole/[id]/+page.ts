import { mockBorehole } from './mock-data';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	// TODO: fetch the borehole from the API using params.id.
	return { borehole: mockBorehole };
};
