import { config } from '#lib/config.ts';
import type { BoreholeRepository } from '#lib/repositories/borehole-repository.ts';
import type { SearchRepository } from '#lib/repositories/search-repository.ts';
import { BoreholeService } from './borehole-service';
import { PipelineService } from './pipeline-service';
import { SearchService } from './search-service';
import { UploadService } from './upload-service';

export { BoreholeService, BoreholeNotFoundError, DocumentNotFoundError } from './borehole-service';
export type { BoreholeListQuery, PagedResult } from './borehole-service';
export { RepositoryError } from '#lib/repositories/borehole-repository.ts';
export { SearchService } from './search-service';
export { PipelineService, PipelineNotFoundError } from './pipeline-service';
export { UploadService, UnsupportedFileError } from './upload-service';

export interface Services {
	boreholes: BoreholeService;
	search: SearchService;
	uploads: UploadService;
	pipelines: PipelineService;
}

/**
 * Composition root: the only place that knows which repository implementation is used.
 * All data comes from the API (ADR-0029). The mock repositories in `repositories/mock/` are kept
 * but not wired in; to use them again, construct them here instead of the API repositories.
 * Pass SvelteKit's `fetch` from the load function.
 */
export async function createServices({
	fetch
}: {
	fetch: typeof globalThis.fetch;
}): Promise<Services> {
	const [
		{ ApiBoreholeRepository },
		{ ApiSearchRepository },
		{ ApiUploadRepository },
		{ MockPipelineRepository }
	] = await Promise.all([
		import('#lib/repositories/api/api-borehole-repository.ts'),
		import('#lib/repositories/api/api-search-repository.ts'),
		import('#lib/repositories/api/api-upload-repository.ts'),
		import('#lib/repositories/mock/mock-pipeline-repository.ts')
	]);
	const options = { baseUrl: config.apiUrl, fetch };
	const boreholes: BoreholeRepository = new ApiBoreholeRepository(options);
	const search: SearchRepository = new ApiSearchRepository(options);
	return {
		boreholes: new BoreholeService(boreholes),
		search: new SearchService(search),
		uploads: new UploadService(new ApiUploadRepository(options)),
		// Placeholder data until the API exposes pipeline runs.
		pipelines: new PipelineService(new MockPipelineRepository())
	};
}
