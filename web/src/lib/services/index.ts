import { config } from '#lib/config.ts';
import type { BoreholeRepository } from '#lib/repositories/borehole-repository.ts';
import type { SearchRepository } from '#lib/repositories/search-repository.ts';
import { BoreholeService } from './borehole-service';
import { SearchService } from './search-service';

export { BoreholeService, BoreholeNotFoundError, DocumentNotFoundError } from './borehole-service';
export type { BoreholeListQuery, PagedResult } from './borehole-service';
export { SearchService } from './search-service';

export interface Services {
	boreholes: BoreholeService;
	search: SearchService;
}

/**
 * Composition root: the only place that knows which repository implementation is used.
 * Pass SvelteKit's `fetch` from the load function.
 */
export async function createServices({
	fetch
}: {
	fetch: typeof globalThis.fetch;
}): Promise<Services> {
	let boreholes: BoreholeRepository;
	let search: SearchRepository;
	if (config.dataSource === 'api') {
		const [{ ApiBoreholeRepository }, { ApiSearchRepository }] = await Promise.all([
			import('#lib/repositories/api/api-borehole-repository.ts'),
			import('#lib/repositories/api/api-search-repository.ts')
		]);
		const options = { baseUrl: config.apiUrl, fetch };
		boreholes = new ApiBoreholeRepository(options);
		search = new ApiSearchRepository(options);
	} else {
		// Dynamic import keeps faker and the mock data out of API-mode code paths.
		const [{ MockBoreholeRepository }, { MockSearchRepository }] = await Promise.all([
			import('#lib/repositories/mock/mock-borehole-repository.ts'),
			import('#lib/repositories/mock/mock-search-repository.ts')
		]);
		boreholes = new MockBoreholeRepository();
		search = new MockSearchRepository();
	}
	return { boreholes: new BoreholeService(boreholes), search: new SearchService(search) };
}
